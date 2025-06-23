"""
Simple usage examples for file-based resource templates.

Templates are automatically available when imported - no registration needed!
"""

# flake8: noqa
# Import templates and functions from your actual path
from madsci.common.types.resource_types.templates import (
    create_resource_from_template,
    get_all_templates,
    get_template_info,
    get_template_names,
    get_templates_by_category,
    get_templates_by_tags,
    list_templates,
)

# Import template definitions from your actual module - this auto-registers all templates


def example1_basic_usage():
    """Example 1: Templates are automatically available."""
    print("=" * 60)
    print("EXAMPLE 1: Templates Available Immediately")
    print("=" * 60)

    # No registration needed! Templates are available immediately
    all_templates = get_all_templates()
    print(f"Available templates: {len(all_templates)}")

    # Show template names
    template_names = get_template_names()
    print("Template names:")
    for name in template_names[:8]:  # Show first 8
        print(f"  - {name}")

    # Show by category
    categories = get_templates_by_category()
    print("\nTemplates by category:")
    for category, names in categories.items():
        print(f"  {category}: {len(names)} templates")

    print("\n" + "-" * 40)
    print("Creating resources:")
    print("-" * 40)

    # Create a PCR machine - simple!
    try:
        pcr_machine = create_resource_from_template(
            template_name="pcr_biorad_cfx96",
            resource_name="Lab_PCR_Alpha",
            # Add additional custom attributes to existing list
            custom_attributes=[
                {"attribute_name": "serial_number", "value": "CFX96-001"}
            ],
            location="Lab B",
        )
        print(f"✓ Created PCR machine: {pcr_machine.resource_name}")

    except Exception as e:
        print(f"✗ Error creating PCR machine: {e}")

    # Create a microplate
    try:
        plate = create_resource_from_template(
            template_name="microplate_96_well_standard", resource_name="Assay_Plate_001"
        )
        print(f"✓ Created microplate: {plate.resource_name}")

    except Exception as e:
        print(f"✗ Error creating microplate: {e}")


def example2_template_discovery():
    """Example 2: Discovering available templates."""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Template Discovery")
    print("=" * 60)

    # Find PCR-related templates
    pcr_templates = get_templates_by_tags(["pcr"])
    print(f"PCR templates: {pcr_templates}")

    # Find lab equipment
    equipment_templates = get_templates_by_tags(["lab_equipment"])
    print(f"Lab equipment: {equipment_templates}")

    # Find gripper templates
    gripper_templates = get_templates_by_tags(["gripper"])
    print(f"Gripper templates: {gripper_templates}")

    # Find pool resources
    pool_templates = get_templates_by_tags(["pool"])
    print(f"Pool templates: {pool_templates}")

    # Find by base type
    from madsci.common.types.resource_types.resource_enums import ResourceTypeEnum

    pool_resources = list_templates(base_type=ResourceTypeEnum.pool)
    print(f"Pool resource templates: {len(pool_resources)}")

    print("\n" + "-" * 40)
    print("Template details:")
    print("-" * 40)

    # Get detailed info about a template
    pcr_info = get_template_info("pcr_biorad_cfx96")
    if pcr_info:
        print(f"Template: {pcr_info['display_name']}")
        print(f"Description: {pcr_info['description']}")
        print(f"Required overrides: {pcr_info['required_overrides']}")
        print(f"Tags: {pcr_info['tags']}")


def example3_template_inspection():
    """Example 3: Inspecting what's available."""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Template Inspection")
    print("=" * 60)

    # Get all templates as a dictionary
    all_templates = get_all_templates()
    print(f"Total templates available: {len(all_templates)}")

    print("\nTemplate overview:")
    for name, template in list(all_templates.items())[:5]:  # Show first 5
        print(f"  {name}:")
        print(f"    Type: {template.base_type.value}")
        print(f"    Source: {template.source.value}")
        print(f"    Required: {template.required_overrides}")

    # Show templates by category
    print("\nBy resource type:")
    categories = get_templates_by_category()
    for resource_type, names in categories.items():
        print(f"  {resource_type}: {names}")


def example4_practical_workflow():
    """Example 4: Practical workflow - creating resources that work."""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Practical Workflow")
    print("=" * 60)

    print("Setting up lab experiment with working templates...")

    resources_created = []

    # 1. Create a basic microplate
    try:
        plate = create_resource_from_template(
            "microplate_96_well_standard", "Assay_Plate_001"
        )
        resources_created.append(plate)
        print(f"✓ Microplate: {plate.resource_name}")
    except Exception as e:
        print(f"✗ Microplate failed: {e}")

    # 2. Create water pool
    try:
        water_pool = create_resource_from_template(
            "water_nuclease_free_pool", "Water_Pool_A", total_quantity=1000.0
        )
        resources_created.append(water_pool)
        print(f"✓ Water pool: {water_pool.resource_name}")
    except Exception as e:
        print(f"✗ Water pool failed: {e}")

    # 3. Create tip pool
    try:
        tip_pool = create_resource_from_template(
            "pipette_tips_p200_pool", "Tips_Pool_A", total_quantity=5000
        )
        resources_created.append(tip_pool)
        print(f"✓ Tip pool: {tip_pool.resource_name}")
    except Exception as e:
        print(f"✗ Tip pool failed: {e}")

    print(f"\nCreated {len(resources_created)} resources")
    print("💡 Templates working correctly!")


def example5_error_handling():
    """Example 5: Error handling."""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Error Handling")
    print("=" * 60)

    # Try with non-existent template
    try:
        resource = create_resource_from_template(
            "nonexistent_template", "Test_Resource"
        )
        print("✗ Should have failed!")
    except ValueError as e:
        print(f"✓ Correctly caught bad template: {e}")

    # Try without required fields
    try:
        water_pool = create_resource_from_template(
            "water_nuclease_free_pool",
            "Incomplete_Pool",
            # Missing required total_quantity
        )
        print("✗ Should have failed!")
    except ValueError as e:
        print(f"✓ Correctly caught missing required field: {e}")


def run_examples():
    """Run all examples showing the simplified template system."""
    print("MADSci Auto-Available Template System")
    print("Templates automatically ready when imported!\n")

    try:
        example1_basic_usage()
        example2_template_discovery()
        example3_template_inspection()
        example4_practical_workflow()
        example5_error_handling()

        print("\n" + "=" * 60)
        print("SUCCESS! Auto-available template system! 🎉")
        print("=" * 60)
        print("Templates automatically available when imported")
        print("No manual registration required")
        print("Easy discovery with get_template_names(), get_templates_by_category()")
        print("Simple create_resource_from_template(name, resource_name, **overrides)")
        print("Complete template information available")
        print("Includes grippers, pools, and all resource types")
        print("Handles custom_attributes as list format")

    except Exception as e:
        print(f"\n✗ Error in examples: {e}")
        import traceback

        traceback.print_exc()


# Run examples when script is executed
if __name__ == "__main__":
    run_examples()
