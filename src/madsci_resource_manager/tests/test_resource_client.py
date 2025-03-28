"""Automated pytest unit tests for the madsci resource client."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from madsci.client.resource_client import ResourceClient
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.base_types import new_ulid_str
from madsci.common.types.resource_types import Consumable, ResourceDefinition
from madsci.common.types.resource_types.definitions import ResourceManagerDefinition
from madsci.resource_manager.resource_interface import (
    Container,
    ResourceInterface,
    ResourceTable,
    Stack,
)
from madsci.resource_manager.resource_server import create_resource_server
from madsci.resource_manager.resource_tables import Resource, create_session
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


@pytest.fixture
def client(test_client: TestClient) -> Generator[ResourceClient, None, None]:
    """Fixture for ResourceClient patched to use TestClient"""
    with patch("madsci.client.resource_client.requests") as mock_requests:

        def post_no_timeout(*args: Any, **kwargs: Any) -> Any:
            kwargs.pop("timeout", None)
            return test_client.post(*args, **kwargs)

        mock_requests.post.side_effect = post_no_timeout

        def get_no_timeout(*args: Any, **kwargs: Any) -> Any:
            kwargs.pop("timeout", None)
            return test_client.get(*args, **kwargs)

        mock_requests.get.side_effect = get_no_timeout

        def delete_no_timeout(*args: Any, **kwargs: Any) -> Any:
            kwargs.pop("timeout", None)
            return test_client.delete(*args, **kwargs)

        mock_requests.delete.side_effect = delete_no_timeout
        yield ResourceClient(url="http://testserver")


def test_add_resource(client: ResourceClient) -> None:
    """Test adding a resource using ResourceClient"""
    resource = Resource()
    added_resource = client.add_resource(resource)
    assert added_resource.resource_id == resource.resource_id


def test_update_resource(client: ResourceClient) -> None:
    """Test updating a resource using ResourceClient"""
    resource = Resource()
    client.add_resource(resource)
    resource.resource_name = "Updated Name"
    updated_resource = client.update_resource(resource)
    assert updated_resource.resource_name == "Updated Name"


def test_get_resource(client: ResourceClient) -> None:
    """Test getting a resource using ResourceClient"""
    resource = Resource()
    client.add_resource(resource)
    fetched_resource = client.get_resource(resource.resource_id)
    assert fetched_resource.resource_id == resource.resource_id


def test_query_resource(client: ResourceClient) -> None:
    """Test querying a resource using ResourceClient"""
    resource = Resource(resource_name="Test Resource")
    client.add_resource(resource)
    queried_resource = client.query_resource(resource_name="Test Resource")
    assert queried_resource.resource_id == resource.resource_id


def test_remove_resource(client: ResourceClient) -> None:
    """Test removing a resource using ResourceClient"""
    resource = Resource()
    client.add_resource(resource)
    removed_resource = client.remove_resource(resource.resource_id)
    assert removed_resource.resource_id == resource.resource_id
    assert removed_resource.removed is True


def test_query_history(client: ResourceClient) -> None:
    """Test querying resource history using ResourceClient"""
    resource = Resource(resource_name="History Test Resource")
    client.add_resource(resource)
    client.remove_resource(resource.resource_id)
    history = client.query_history(resource_id=resource.resource_id)
    assert len(history) > 0
    assert history[0]["resource_id"] == resource.resource_id


def test_restore_deleted_resource(client: ResourceClient) -> None:
    """Test restoring a deleted resource using ResourceClient"""
    resource = Resource(resource_name="Resource to Restore")
    client.add_resource(resource)
    client.remove_resource(resource.resource_id)
    restored_resource = client.restore_deleted_resource(resource.resource_id)
    assert restored_resource.resource_id == resource.resource_id
    assert restored_resource.removed is False


def test_push(client: ResourceClient) -> None:
    """Test pushing a resource onto a stack using ResourceClient"""
    stack = Stack()
    client.add_resource(stack)
    resource = Resource()
    updated_stack = client.push(stack, resource)
    assert len(updated_stack.children) == 1
    assert updated_stack.children[0].resource_id == resource.resource_id


def test_pop(client: ResourceClient) -> None:
    """Test popping a resource from a stack using ResourceClient"""
    stack = Stack()
    client.add_resource(stack)
    resource = Resource()
    client.push(stack, resource)
    popped_resource, updated_stack = client.pop(stack)
    assert popped_resource.resource_id == resource.resource_id
    assert len(updated_stack.children) == 0


def test_set_child(client: ResourceClient) -> None:
    """Test setting a child resource in a container using ResourceClient"""
    container = Container()
    client.add_resource(container)
    resource = Resource()
    updated_container = client.set_child(container, "test_key", resource)
    assert "test_key" in updated_container.children
    assert updated_container.children["test_key"].resource_id == resource.resource_id


def test_remove_child(client: ResourceClient) -> None:
    """Test removing a child resource from a container using ResourceClient"""
    container = Container()
    client.add_resource(container)
    resource = Resource()
    client.set_child(container, "test_key", resource)
    updated_container = client.remove_child(container, "test_key")
    assert "test_key" not in updated_container.children


def test_set_quantity(client: ResourceClient) -> None:
    """Test setting the quantity of a resource using ResourceClient"""
    resource = Consumable(quantity=0)
    client.add_resource(resource)
    updated_resource = client.set_quantity(resource, 42)
    assert updated_resource.quantity == 42


def test_set_capacity(client: ResourceClient) -> None:
    """Test setting the capacity of a resource using ResourceClient"""
    resource = Consumable(quantity=0)
    client.add_resource(resource)
    updated_resource = client.set_capacity(resource, 42)
    assert updated_resource.capacity == 42


def test_remove_capacity_limit(client: ResourceClient) -> None:
    """Test removing the capacity limit of a resource using ResourceClient"""
    resource = Consumable(quantity=5, capacity=10)
    client.add_resource(resource)
    updated_resource = client.remove_capacity_limit(resource)
    assert updated_resource.capacity is None


def test_change_quantity_by_increase(client: ResourceClient) -> None:
    """Test increasing the quantity of a resource using ResourceClient"""
    resource = Consumable(quantity=10)
    client.add_resource(resource)
    updated_resource = client.change_quantity_by(resource, 5)
    assert updated_resource.quantity == 15


def test_change_quantity_by_decrease(client: ResourceClient) -> None:
    """Test decreasing the quantity of a resource using ResourceClient"""
    resource = Consumable(quantity=10)
    client.add_resource(resource)
    updated_resource = client.change_quantity_by(resource, -5)
    assert updated_resource.quantity == 5


def test_increase_quantity_positive(client: ResourceClient) -> None:
    """Test increasing the quantity of a resource using ResourceClient with a positive amount"""
    resource = Consumable(quantity=10)
    client.add_resource(resource)
    updated_resource = client.increase_quantity(resource, 5)
    assert updated_resource.quantity == 15


def test_increase_quantity_negative(client: ResourceClient) -> None:
    """Test increasing the quantity of a resource using ResourceClient with a negative amount"""
    resource = Consumable(quantity=10)
    client.add_resource(resource)
    updated_resource = client.increase_quantity(resource, -5)
    assert updated_resource.quantity == 15


def test_decrease_quantity_positive(client: ResourceClient) -> None:
    """Test decreasing the quantity of a resource using ResourceClient with a positive amount"""
    resource = Consumable(quantity=10)
    client.add_resource(resource)
    updated_resource = client.decrease_quantity(resource, 5)
    assert updated_resource.quantity == 5


def test_decrease_quantity_negative(client: ResourceClient) -> None:
    """Test decreasing the quantity of a resource using ResourceClient with a negative amount"""
    resource = Consumable(quantity=10)
    client.add_resource(resource)
    updated_resource = client.decrease_quantity(resource, -5)
    assert updated_resource.quantity == 5


def test_empty_consumable(client: ResourceClient) -> None:
    """Test emptying a consumable using ResourceClient"""
    resource = Consumable(quantity=10)
    client.add_resource(resource)
    emptied_resource = client.empty(resource)
    assert emptied_resource.quantity == 0


def test_empty_container(client: ResourceClient) -> None:
    """Test emptying a container using ResourceClient"""
    container = Container()
    client.add_resource(container)
    resource = Resource()
    client.set_child(container, "test_key", resource)
    emptied_container = client.empty(container)
    assert len(emptied_container.children) == 0


def test_fill_resource(client: ResourceClient) -> None:
    """Test filling a resource using ResourceClient"""
    resource = Consumable(quantity=0, capacity=10)
    client.add_resource(resource)
    filled_resource = client.fill(resource)
    assert filled_resource.quantity == filled_resource.capacity


def test_init_resource(client: ResourceClient) -> None:
    """Test querying or adding a resource using ResourceClient"""
    definition = ResourceDefinition(
        resource_name="Init Test Resource",
        owner=OwnershipInfo(node_id=new_ulid_str()),
    )
    init_resource = client.init_resource(definition)
    assert init_resource.resource_name == "Init Test Resource"

    second_init_resource = client.init_resource(definition)
    assert second_init_resource.resource_name == "Init Test Resource"
    assert second_init_resource.resource_id == init_resource.resource_id
    assert second_init_resource.owner.node_id == init_resource.owner.node_id
