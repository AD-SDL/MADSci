"""Automated pytest unit tests for the madsci resource client."""

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import pytest
from madsci.client.resource_client import ResourceClient
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.resource_types import Consumable, ResourceDefinition
from madsci.common.types.resource_types.definitions import ResourceManagerDefinition
from madsci.common.types.resource_types.resource_enums import ContainerTypeEnum
from madsci.common.utils import new_ulid_str
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

        def put_no_timeout(*args: Any, **kwargs: Any) -> Any:
            kwargs.pop("timeout", None)
            return test_client.put(*args, **kwargs)

        mock_requests.put.side_effect = put_no_timeout

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


def test_create_template(client: ResourceClient) -> None:
    """Test creating a template using ResourceClient"""
    # Create a sample resource to use as template
    plate_resource = Container(
        resource_name="SamplePlate96Well",
        base_type=ContainerTypeEnum.container,
        resource_class="Plate96Well",
        rows=8,
        columns=12,
        capacity=96,
        attributes={"well_volume": 200, "material": "polystyrene"},
    )

    # Create template
    template = client.create_template(
        resource=plate_resource,
        template_name="test_plate_template",
        description="A template for creating 96-well plates",
        required_overrides=["resource_name"],
        source="system",
        tags=["plate", "96-well", "testing"],
        created_by="test_system",
    )

    assert template.resource_name == "SamplePlate96Well"
    assert template.rows == 8
    assert template.columns == 12
    assert template.capacity == 96


def test_get_template(client: ResourceClient) -> None:
    """Test getting a template using ResourceClient"""
    # First create a template
    resource = Container(resource_name="TestContainer", capacity=100)
    client.create_template(
        resource=resource,
        template_name="get_test_template",
        description="Template for get test",
    )

    # Get the template
    retrieved_template = client.get_template("get_test_template")

    assert retrieved_template is not None
    assert retrieved_template.resource_name == "TestContainer"
    assert retrieved_template.capacity == 100


def test_get_template_not_found(client: ResourceClient) -> None:
    """Test getting a non-existent template returns None"""
    template = client.get_template("non_existent_template")
    assert template is None


def test_list_templates(client: ResourceClient) -> None:
    """Test listing templates using ResourceClient"""
    # Create multiple templates
    resource1 = Container(resource_name="Container1", capacity=50)
    resource2 = Resource(resource_name="Resource2")

    client.create_template(
        resource=resource1,
        template_name="list_test_template_1",
        description="First template",
        source="system",
        tags=["container", "test"],
    )

    client.create_template(
        resource=resource2,
        template_name="list_test_template_2",
        description="Second template",
        source="node",
        tags=["resource", "test"],
    )

    # List all templates
    all_templates = client.list_templates()
    template_names = [t.resource_name for t in all_templates]
    assert "Container1" in template_names
    assert "Resource2" in template_names

    # Filter by source
    system_templates = client.list_templates(source="system")
    assert len(system_templates) >= 1

    # Filter by tags
    test_templates = client.list_templates(tags=["test"])
    assert len(test_templates) >= 2


def test_get_template_info(client: ResourceClient) -> None:
    """Test getting template metadata using ResourceClient"""
    resource = Container(resource_name="InfoTestContainer")
    client.create_template(
        resource=resource,
        template_name="info_test_template",
        description="Template for info test",
        required_overrides=["resource_name", "capacity"],
        source="system",
        tags=["info", "test"],
        created_by="test_user",
        version="2.0.0",
    )

    template_info = client.get_template_info("info_test_template")

    assert template_info is not None
    assert template_info["description"] == "Template for info test"
    assert template_info["required_overrides"] == ["resource_name", "capacity"]
    assert template_info["source"] == "system"
    assert template_info["tags"] == ["info", "test"]
    assert template_info["created_by"] == "test_user"
    assert template_info["version"] == "2.0.0"


def test_update_template(client: ResourceClient) -> None:
    """Test updating a template using ResourceClient"""
    resource = Container(resource_name="UpdateTestContainer")
    client.create_template(
        resource=resource,
        template_name="update_test_template",
        description="Original description",
        tags=["original"],
    )

    # Update the template
    updated_template = client.update_template(
        "update_test_template",
        {
            "description": "Updated description",
            "tags": ["updated", "modified"],
            "source": "node",
            "capacity": 200,
        },
    )

    assert updated_template.resource_name == "UpdateTestContainer"

    # Verify changes in metadata
    template_info = client.get_template_info("update_test_template")
    assert template_info["description"] == "Updated description"
    assert template_info["tags"] == ["updated", "modified"]
    assert template_info["source"] == "node"


def test_delete_template(client: ResourceClient) -> None:
    """Test deleting a template using ResourceClient"""
    resource = Resource(resource_name="DeleteTestResource")
    client.create_template(
        resource=resource,
        template_name="delete_test_template",
        description="Template to be deleted",
    )

    # Verify template exists
    assert client.get_template("delete_test_template") is not None

    # Delete template
    deleted = client.delete_template("delete_test_template")
    assert deleted is True

    # Verify template is gone
    assert client.get_template("delete_test_template") is None

    # Try to delete non-existent template
    deleted_again = client.delete_template("delete_test_template")
    assert deleted_again is False


def test_create_resource_from_template(client: ResourceClient) -> None:
    """Test creating a resource from a template using ResourceClient"""
    # Create template
    plate_resource = Container(
        resource_name="TemplatePlate",
        base_type=ContainerTypeEnum.container,
        rows=8,
        columns=12,
        capacity=96,
        attributes={"material": "plastic"},
    )

    client.create_template(
        resource=plate_resource,
        template_name="resource_creation_template",
        description="Template for resource creation test",
        required_overrides=["resource_name"],
    )

    # Create resource from template
    new_resource = client.create_resource_from_template(
        template_name="resource_creation_template",
        resource_name="CreatedPlate001",
        overrides={"attributes": {"material": "glass", "batch": "B001"}},
        add_to_database=True,
    )

    assert new_resource.resource_name == "CreatedPlate001"
    assert new_resource.rows == 8
    assert new_resource.columns == 12
    assert new_resource.capacity == 96
    assert new_resource.attributes["material"] == "glass"
    assert new_resource.attributes["batch"] == "B001"

    # Verify it's a different resource than the template
    template = client.get_template("resource_creation_template")
    assert new_resource.resource_id != template.resource_id


def test_create_resource_from_template_missing_required(client: ResourceClient) -> None:
    """Test creating resource from template with missing required fields fails"""
    resource = Container(resource_name="RequiredTestContainer")
    client.create_template(
        resource=resource,
        template_name="required_fields_template",
        description="Template with required fields",
        required_overrides=["resource_name", "attributes.batch_number"],
    )

    # Should fail due to missing required field
    with pytest.raises((ValueError, Exception)):  # Could be ValueError or HTTPError
        client.create_resource_from_template(
            template_name="required_fields_template",
            resource_name="TestResource",
            overrides={"attributes": {"other_field": "value"}},  # Missing batch_number
            add_to_database=False,
        )


def test_create_resource_from_nonexistent_template(client: ResourceClient) -> None:
    """Test creating resource from non-existent template fails"""
    with pytest.raises((ValueError, Exception)):  # Could be ValueError or HTTPError
        client.create_resource_from_template(
            template_name="nonexistent_template",
            resource_name="TestResource",
            add_to_database=False,
        )


def test_get_templates_by_category(client: ResourceClient) -> None:
    """Test getting templates by category using ResourceClient"""
    # Create templates with different base types
    container = Container(resource_name="CategoryContainer")
    resource = Resource(resource_name="CategoryResource")

    client.create_template(
        resource=container,
        template_name="category_container_template",
        description="Container template",
    )

    client.create_template(
        resource=resource,
        template_name="category_resource_template",
        description="Resource template",
    )

    categories = client.get_templates_by_category()

    assert isinstance(categories, dict)
    assert len(categories) >= 1

    # Check that templates are categorized by base_type
    for category, template_names in categories.items():  # noqa
        assert isinstance(template_names, list)
        assert len(template_names) > 0


def test_template_with_complex_attributes(client: ResourceClient) -> None:
    """Test template creation and usage with complex nested attributes"""
    complex_resource = Container(
        resource_name="ComplexPlate",
        capacity=384,
        attributes={
            "plate_type": "384-well",
            "specifications": {
                "well_volume": 50,
                "material": "polystyrene",
                "coating": "tissue_culture",
            },
            "metadata": {"manufacturer": "TestCorp", "lot_number": "LOT12345"},
        },
    )

    client.create_template(
        resource=complex_resource,
        template_name="complex_template",
        description="Template with complex attributes",
        required_overrides=["resource_name", "attributes.metadata.lot_number"],
    )

    # Create resource with overrides
    new_resource = client.create_resource_from_template(
        template_name="complex_template",
        resource_name="ComplexPlate001",
        overrides={
            "attributes": {
                **complex_resource.attributes,
                "metadata": {
                    **complex_resource.attributes["metadata"],
                    "lot_number": "LOT99999",
                    "expiry_date": "2026-01-01",
                },
            }
        },
        add_to_database=False,
    )

    assert new_resource.resource_name == "ComplexPlate001"
    assert new_resource.attributes["metadata"]["lot_number"] == "LOT99999"
    assert new_resource.attributes["metadata"]["expiry_date"] == "2026-01-01"
    assert new_resource.attributes["specifications"]["well_volume"] == 50


def test_minimal_template(client: ResourceClient) -> None:
    """Test creating and using a minimal template"""
    minimal_resource = Resource(resource_name="MinimalResource")

    template = client.create_template(
        resource=minimal_resource,
        template_name="minimal_template",
        description="Minimal template test",
    )

    assert template.resource_name == "MinimalResource"

    # Create resource from minimal template
    new_resource = client.create_resource_from_template(
        template_name="minimal_template",
        resource_name="MinimalCopy",
        add_to_database=False,
    )

    assert new_resource.resource_name == "MinimalCopy"
    assert type(new_resource).__name__ == "Resource"
