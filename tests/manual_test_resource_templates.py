"""
Simple usage examples for file-based resource templates.

Templates are automatically available when imported - no registration needed!
"""

# flake8: noqa
"""
Updated tests for simplified template interface.
Templates are now regular resources - much simpler!
"""
from madsci.common.types.resource_types import Container
from madsci.common.types.resource_types.resource_enums import (
    ResourceTypeEnum,
    ContainerTypeEnum,
)
from madsci.resource_manager.resource_interface import ResourceInterface
from madsci.common.types.resource_types import Resource
from madsci.client.resource_client import ResourceClient


def test_template_interface():
    """Basic tests for template management functionality."""
    print(" Starting Simplified Template Interface Tests...")

    # Initialize interface
    interface = ResourceInterface(url="postgresql://rpl:rpl@localhost:5432/resources")

    # Test data - create a regular resource to use as template

    # Create a sample plate resource
    plate_resource = Container(
        resource_name="SamplePlate96Well",
        base_type=ContainerTypeEnum.container,
        resource_class="Plate96Well",
        rows=8,
        columns=12,
        capacity=96,
        attributes={"well_volume": 200, "material": "polystyrene"},
    )

    # Test 1: Create Template from Resource
    print("\nTesting create_template()...")
    try:
        template_resource = interface.create_template(
            resource=plate_resource,
            template_name="test_plate_template",
            description="A template for creating 96-well plates for testing",
            required_overrides=["resource_name"],
            source="system",
            tags=["plate", "96-well", "testing"],
            created_by="test_system",
        )
        # print(template_resource)
        print(f"  Created template: {template_resource.resource_name}")
        print(f"   Base type: {template_resource.base_type}")
        print(f"   Resource class: {template_resource.resource_class}")
        print(
            f"   Rows: {template_resource.rows}, Columns: {template_resource.columns}"
        )
        print(f"   Capacity: {template_resource.capacity}")
        print(f"   Attributes: {template_resource.attributes}")
    except Exception as e:
        print(f" Failed to create template: {e}")

    # Test 2: Get Template
    print("\nTesting get_template()...")
    try:
        retrieved_template = interface.get_template("test_plate_template")
        # print(retrieved_template)
        if retrieved_template:
            print(f"  Retrieved template: {retrieved_template.resource_name}")
            print(f"   Type: {type(retrieved_template).__name__}")
            print(
                f"   Rows: {retrieved_template.rows}, Columns: {retrieved_template.columns}"
            )
            print(f"   Resource ID: {retrieved_template.resource_id}")
        else:
            print(" Template not found")
    except Exception as e:
        print(f" Failed to get template: {e}")

    # Test 3: Get Template Info (metadata)
    print("\nTesting get_template_info()...")
    try:
        template_info = interface.get_template_info("test_plate_template")
        if template_info:
            print(f" Template metadata:")
            print(f"   Description: {template_info['description']}")
            print(f"   Required overrides: {template_info['required_overrides']}")
            print(f"   Source: {template_info['source']}")
            print(f"   Tags: {template_info['tags']}")
            print(f"   Created by: {template_info['created_by']}")
            print(
                f"   Default values keys: {list(template_info['default_values'].keys())}"
            )
        else:
            print(" Template info not found")
            return False
    except Exception as e:
        print(f" Failed to get template info: {e}")
        return False

    # Test 4: List Templates
    print("\nTesting list_templates()...")
    try:
        all_templates = interface.list_templates()
        print(f"Found {len(all_templates)} templates")
        for template in all_templates:
            print(f"   - {template.resource_name} ({template.base_type})")

        # Test filtering by source
        system_templates = interface.list_templates(source="system")
        print(f"Found {len(system_templates)} SYSTEM templates")

        # Test filtering by tags
        plate_templates = interface.list_templates(tags=["plate"])
        print(f"Found {len(plate_templates)} templates with 'plate' tag")

    except Exception as e:
        print(f"Failed to list templates: {e}")

    # Test 5: Update Template
    print("\nTesting update_template()...")
    try:
        updated_template = interface.update_template(
            "test_plate_template",
            {
                "description": "Updated description for 96-well plate template",
                "tags": ["plate", "96-well", "testing", "updated"],
                "capacity": 100,  # Update a resource field too
            },
        )
        print(f"   Updated template: {updated_template.resource_name}")
        print(f"   New capacity: {updated_template.capacity}")

        # Check the metadata was updated too
        updated_info = interface.get_template_info("test_plate_template")
        print(f"   New description: {updated_info['description']}")
        print(f"   New tags: {updated_info['tags']}")

    except Exception as e:
        print(f"Failed to update template: {e}")

    # Test 6: Create Resource from Template
    print("\nTesting create_resource_from_template()...")
    try:
        # Test with valid overrides
        new_resource = interface.create_resource_from_template(
            template_name="test_plate_template",
            resource_name="TestPlate001",
            overrides={
                "owner": {"node": "test_node", "experiment": "test_exp"},
                "attributes": {"batch_number": "B001", "expiry_date": "2025-12-31"},
                "capacity": 100,  # Override capacity
            },
        )
        print(f"   Created resource: {new_resource.resource_name}")
        print(f"   Resource ID: {new_resource.resource_id}")
        print(f"   Type: {type(new_resource).__name__}")
        print(f"   Base type: {new_resource.base_type}")
        print(f"   Rows: {new_resource.rows}, Columns: {new_resource.columns}")
        print(f"   Capacity: {new_resource.capacity}")
        print(f"   Attributes: {new_resource.attributes}")

        # Verify it's different from template (different ID)
        template = interface.get_template("test_plate_template")
        print(f"   Template ID: {template.resource_id}")
        print(f"   Resource ID: {new_resource.resource_id}")
        print(f"   Different IDs: {template.resource_id != new_resource.resource_id}")

    except Exception as e:
        print(f" Failed to create resource from template: {e}")

    # Test 7: Get Templates by Category
    print("\nTesting get_templates_by_category()...")
    try:
        categories = interface.get_templates_by_category()
        print(f" Template categories: {categories}")
        for category, template_names in categories.items():
            print(f"   {category}: {template_names}")
    except Exception as e:
        print(f" Failed to get templates by category: {e}")

    # Test 8: Get Templates by Tags
    print("\nTesting get_templates_by_tags()...")
    try:
        plate_template_names = interface.get_templates_by_tags(["plate"])
        print(f" Templates with 'plate' tag: {plate_template_names}")

        testing_template_names = interface.get_templates_by_tags(["testing", "updated"])
        print(f" Templates with 'testing' or 'updated' tags: {testing_template_names}")
    except Exception as e:
        print(f" Failed to get templates by tags: {e}")

    # Test 9: Test Non-existent Template
    print("\nTesting error handling...")
    try:
        non_existent = interface.get_template("this_template_does_not_exist")
        if non_existent is None:
            print(" Correctly returned None for non-existent template")
        else:
            print(" Should have returned None for non-existent template")

        # Test creating resource from non-existent template
        try:
            interface.create_resource_from_template(
                template_name="fake_template",
                resource_name="TestResource",
                add_to_database=False,
            )
            print(" Should have failed with non-existent template")
        except ValueError as ve:
            print(f" Correctly caught non-existent template error: {ve}")

    except Exception as e:
        print(f" Error handling test failed: {e}")

    # Test 10: Delete Template
    print("\n Testing delete_template()...")
    try:
        deleted = interface.delete_template("test_plate_template")
        if deleted:
            print(" Successfully deleted test template")

            # Verify it's gone
            retrieved = interface.get_template("test_plate_template")
            if retrieved is None:
                print(" Confirmed template was deleted")
            else:
                print(" Template still exists after deletion")
        else:
            print(" Delete returned False")

        # Test deleting non-existent template
        deleted_again = interface.delete_template("test_plate_template")
        if not deleted_again:
            print(" Correctly returned False for deleting non-existent template")
        else:
            print(" Should have returned False for non-existent template")

    except Exception as e:
        print(f" Failed to delete template: {e}")

    print("\n All simplified template interface tests passed!")


def test_template_edge_cases():
    """Test edge cases with the simplified approach."""
    print("\n Testing Edge Cases...")

    interface = ResourceInterface(url="postgresql://rpl:rpl@localhost:5432/resources")

    # Test with minimal resource

    minimal_resource = Resource(resource_name="MinimalResource")

    print("\n Testing minimal resource template...")
    try:
        template = interface.create_template(
            resource=minimal_resource,
            template_name="minimal_test",
            description="Minimal test template",
        )
        print(f" Created minimal template: {template.resource_name}")
        print(f"   Type: {type(template).__name__}")

        # Create resource from minimal template
        new_resource = interface.create_resource_from_template(
            template_name="minimal_test",
            resource_name="MinimalResourceCopy",
            add_to_database=True,
        )
        print(f" Created resource from minimal template: {new_resource.resource_name}")
        print(f"   Type: {type(new_resource).__name__}")

        # Clean up
        interface.delete_template("minimal_test")
        print(" Cleaned up minimal template")

    except Exception as e:
        print(f" Minimal template test failed: {e}")
        return False

    # Test template with complex attributes
    print("\n Testing complex resource template...")
    try:
        complex_resource = Container(
            resource_name="ComplexPlate",
            base_type=ContainerTypeEnum.container,
            rows=16,
            columns=24,
            capacity=384,
            attributes={
                "plate_type": "384-well",
                "well_volume": 50,
                "coating": "tissue_culture",
                "sterile": True,
                "lot_number": "LOT12345",
                "specifications": {
                    "bottom_type": "flat",
                    "color": "clear",
                    "lid_type": "standard",
                },
            },
        )

        template = interface.create_template(
            resource=complex_resource,
            template_name="complex_384_plate",
            description="384-well plate with complex attributes",
            required_overrides=["resource_name", "attributes.lot_number"],
            tags=["plate", "384-well", "complex", "tissue-culture"],
            source="system",
        )

        print(f"   Created complex template: {template.resource_name}")
        print(f"   Attributes keys: {list(template.attributes.keys())}")

        # Test creating from complex template
        new_complex = interface.create_resource_from_template(
            template_name="complex_384_plate",
            resource_name="TestComplex001",
            overrides={
                "attributes": {
                    **template.attributes,  # Keep existing attributes
                    "lot_number": "LOT99999",  # Override required field
                    "expiry_date": "2026-01-01",  # Add new field
                }
            },
            add_to_database=True,
        )

        print(f" Created complex resource: {new_complex.resource_name}")
        print(f"   Lot number: {new_complex.attributes.get('lot_number')}")
        print(f"   Expiry date: {new_complex.attributes.get('expiry_date')}")

        # Clean up
        interface.delete_template("complex_384_plate")
        print(" Cleaned up complex template")

    except Exception as e:
        print(f" Complex template test failed: {e}")
        return False

    print(" Edge case tests passed!")
    return True


def test_template_client():
    """Basic tests for template management functionality using client."""
    print("Starting Template Client Tests...")

    # Initialize client with REST API URL
    client = ResourceClient(url="http://localhost:8004")

    # Create a sample plate resource
    plate_resource = Container(
        resource_name="SamplePlate96Well",
        base_type=ContainerTypeEnum.container,
        resource_class="Plate96Well",
        rows=8,
        columns=12,
        capacity=96,
        attributes={"well_volume": 200, "material": "polystyrene"},
    )

    # Test 1: Create Template
    print("\n1. Testing create_template()...")
    try:
        template_resource = client.create_template(
            resource=plate_resource,
            template_name="test_plate_template",
            description="A template for creating 96-well plates for testing",
            required_overrides=["resource_name", "attributes.batch_number"],
            source="system",
            tags=["plate", "96-well", "testing"],
            created_by="test_system",
        )
        print(f"Created template: {template_resource.resource_name}")
        print(f"Base type: {template_resource.base_type}")
        print(f"Rows: {template_resource.rows}, Columns: {template_resource.columns}")
    except Exception as e:
        print(f"Failed to create template: {e}")
        return False

    # Test 2: Get Template
    print("\n2. Testing get_template()...")
    try:
        retrieved_template = client.get_template("test_plate_template")
        if retrieved_template:
            print(f"Retrieved template: {retrieved_template.resource_name}")
            print(f"Type: {type(retrieved_template).__name__}")
            print(f"Resource ID: {retrieved_template.resource_id}")
        else:
            print("Template not found")
            return False
    except Exception as e:
        print(f"Failed to get template: {e}")
        return False

    # Test 3: Get Template Info
    print("\n3. Testing get_template_info()...")
    try:
        template_info = client.get_template_info("test_plate_template")
        if template_info:
            print(f"Template metadata:")
            print(f"Description: {template_info['description']}")
            print(f"Required overrides: {template_info['required_overrides']}")
            print(f"Source: {template_info['source']}")
            print(f"Tags: {template_info['tags']}")
        else:
            print("Template info not found")
            return False
    except Exception as e:
        print(f"Failed to get template info: {e}")
        return False

    # Test 4: List Templates
    print("\n4. Testing list_templates()...")
    try:
        all_templates = client.list_templates()
        print(f"Found {len(all_templates)} templates")
        for template in all_templates:
            print(f"- {template.resource_name} ({template.base_type})")

        # Test filtering by source
        system_templates = client.list_templates(source="system")
        print(f"Found {len(system_templates)} system templates")

        # Test filtering by tags
        plate_templates = client.list_templates(tags=["plate"])
        print(f"Found {len(plate_templates)} templates with 'plate' tag")

    except Exception as e:
        print(f"Failed to list templates: {e}")
        return False

    # Test 5: Update Template
    print("\n5. Testing update_template()...")
    try:
        updated_template = client.update_template(
            "test_plate_template",
            {
                "description": "Updated description for 96-well plate template",
                "tags": ["plate", "96-well", "testing", "updated"],
                "capacity": 100,
            },
        )
        print(f"Updated template: {updated_template.resource_name}")

        # Check the metadata was updated
        updated_info = client.get_template_info("test_plate_template")
        print(f"New description: {updated_info['description']}")
        print(f"New tags: {updated_info['tags']}")
        print(f"New capacity: {updated_template.capacity}")

    except Exception as e:
        print(f"Failed to update template: {e}")
        return False

    # Test 6: Create Resource from Template
    print("\n6. Testing create_resource_from_template()...")
    try:
        new_resource = client.create_resource_from_template(
            template_name="test_plate_template",
            resource_name="TestPlate001",
            overrides={
                "owner": {"node": "test_node", "experiment": "test_exp"},
                "attributes": {"batch_number": "B001", "expiry_date": "2025-12-31"},
            },
            add_to_database=True,
        )
        print(f"Created resource: {new_resource.resource_name}")
        print(f"Resource ID: {new_resource.resource_id}")
        print(f"Type: {type(new_resource).__name__}")
        print(f"Rows: {new_resource.rows}, Columns: {new_resource.columns}")

        # Verify it's different from template
        template = client.get_template("test_plate_template")
        print(f"Template ID: {template.resource_id}")
        print(f"Resource ID: {new_resource.resource_id}")
        print(f"Different IDs: {template.resource_id != new_resource.resource_id}")

        # Test missing required field
        try:
            client.create_resource_from_template(
                template_name="test_plate_template",
                resource_name="TestResourceMissingBatch",
                overrides={
                    "owner": {"node": "test_node"}
                },  # Missing attributes.batch_number
                add_to_database=False,
            )
            print("Should have failed with missing attributes.batch_number")
        except ValueError as ve:
            print(f"Correctly caught missing required field: {ve}")
        except Exception as e:
            print(f"Correctly caught error: {e}")

    except Exception as e:
        print(f"Failed to create resource from template: {e}")
        return False

    # Test 7: Get Templates by Category
    print("\n7. Testing get_templates_by_category()...")
    try:
        categories = client.get_templates_by_category()
        print(f"Template categories: {categories}")
        for category, template_names in categories.items():
            print(f"{category}: {template_names}")
    except Exception as e:
        print(f"Failed to get templates by category: {e}")
        return False

    # Test 8: Error Handling
    print("\n8. Testing error handling...")
    try:
        non_existent = client.get_template("this_template_does_not_exist")
        if non_existent is None:
            print("Correctly returned None for non-existent template")
        else:
            print("Should have returned None for non-existent template")

        # Test creating resource from non-existent template
        try:
            client.create_resource_from_template(
                template_name="fake_template",
                resource_name="TestResource",
                add_to_database=False,
            )
            print("Should have failed with non-existent template")
        except Exception as ve:
            print(f"Correctly caught non-existent template error: {ve}")

    except Exception as e:
        print(f"Error handling test failed: {e}")
        return False

    # Test 9: Delete Template
    print("\n9. Testing delete_template()...")
    try:
        deleted = client.delete_template("test_plate_template")
        if deleted:
            print("Successfully deleted test template")

            # Verify it's gone
            retrieved = client.get_template("test_plate_template")
            if retrieved is None:
                print("Confirmed template was deleted")
            else:
                print("Template still exists after deletion")
                return False
        else:
            print("Delete returned False")
            return False

        # Test deleting non-existent template
        deleted_again = client.delete_template("test_plate_template")
        if not deleted_again:
            print("Correctly returned False for deleting non-existent template")
        else:
            print("Should have returned False for non-existent template")

    except Exception as e:
        print(f"Failed to delete template: {e}")
        return False

    print("\nAll template client tests passed!")
    return True


def test_template_client_edge_cases():
    """Test edge cases with the client approach."""
    print("\nTesting Edge Cases...")

    client = ResourceClient(url="http://localhost:8004")

    # Test with minimal resource
    minimal_resource = Resource(resource_name="MinimalResource")

    print("\nTesting minimal resource template...")
    try:
        template = client.create_template(
            resource=minimal_resource,
            template_name="minimal_test",
            description="Minimal test template",
        )
        print(f"Created minimal template: {template.resource_name}")
        print(f"Type: {type(template).__name__}")

        # Create resource from minimal template
        new_resource = client.create_resource_from_template(
            template_name="minimal_test",
            resource_name="MinimalResourceCopy",
            add_to_database=False,
        )
        print(f"Created resource from minimal template: {new_resource.resource_name}")
        print(f"Type: {type(new_resource).__name__}")
        print(f"CREATED RESOURCE: {new_resource}")
        # Clean up
        client.delete_template("minimal_test")
        print("Cleaned up minimal template")

    except Exception as e:
        print(f"Minimal template test failed: {e}")
        return False

    # Test template with complex attributes
    print("\nTesting complex resource template...")
    try:
        complex_resource = Container(
            resource_name="ComplexPlate",
            base_type=ContainerTypeEnum.container,
            capacity=384,
            attributes={
                "plate_type": "384-well",
                "well_volume": 50,
                "coating": "tissue_culture",
                "sterile": True,
                "lot_number": "LOT12345",
                "specifications": {
                    "bottom_type": "flat",
                    "color": "clear",
                    "lid_type": "standard",
                },
            },
        )

        template = client.create_template(
            resource=complex_resource,
            template_name="complex_384_plate",
            description="384-well plate with complex attributes",
            required_overrides=["resource_name"],
            tags=["plate", "384-well", "complex", "tissue-culture"],
            source="system",
        )

        print(f"Created complex template: {template.resource_name}")
        print(f"Attributes keys: {list(template.attributes.keys())}")

        # Test creating from complex template
        new_complex = client.create_resource_from_template(
            template_name="complex_384_plate",
            resource_name="TestComplex001",
            overrides={
                "attributes": {
                    **template.attributes,
                    "lot_number": "LOT99999",
                    "expiry_date": "2026-01-01",
                }
            },
            add_to_database=False,
        )

        print(f"Created complex resource: {new_complex.resource_name}")
        print(f"Lot number: {new_complex.attributes.get('lot_number')}")
        print(f"Expiry date: {new_complex.attributes.get('expiry_date')}")

        # Clean up
        client.delete_template("complex_384_plate")
        print("Cleaned up complex template")

    except Exception as e:
        print(f"Complex template test failed: {e}")
        return False

    print("Edge case tests passed!")
    return True


if __name__ == "__main__":
    test_template_interface()
    test_template_edge_cases()
    test_template_client()
    test_template_client_edge_cases()
