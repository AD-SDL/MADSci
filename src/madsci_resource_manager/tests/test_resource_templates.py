# flake8: noqa

"""
Simple examples to understand the ResourceTemplate system step by step.

Let's start with the most basic case and work our way up.
"""

from typing import Dict

from madsci.common.types.resource_types.custom_types import (
    AssetResourceTypeDefinition,
    CustomResourceTypes,
)

# Import ResourceDefinition to resolve forward references
from madsci.common.types.resource_types.resource_enums import ResourceTypeEnum

# Rebuild models to resolve forward references
AssetResourceTypeDefinition.model_rebuild()

from madsci.common.types.resource_types.templates import (
    ResourceTemplate,
    TemplateCreateRequest,
    create_resource_from_template,
    validate_template,
)


def step1_minimal_custom_type():
    """Step 1: Create the most minimal custom type possible."""
    print("=" * 50)
    print("STEP 1: Creating minimal custom type")
    print("=" * 50)

    # Simplest possible custom type - just a basic asset with no custom attributes
    simple_asset_type = AssetResourceTypeDefinition(
        type_name="simple_asset",
        type_description="A simple asset with no custom attributes",
        base_type=ResourceTypeEnum.asset,
        parent_types=["asset"],
        # custom_attributes=None  # Start with no custom attributes
    )

    print(f"✓ Created custom type: {simple_asset_type.type_name}")
    print(f"  Base type: {simple_asset_type.base_type}")
    print(f"  Description: {simple_asset_type.type_description}")

    return simple_asset_type


def step2_simple_template(custom_type):
    """Step 2: Create a simple template."""
    print("\n" + "=" * 50)
    print("STEP 2: Creating simple template")
    print("=" * 50)

    # Simplest possible template
    simple_template = ResourceTemplate(
        template_name="basic_asset_template",
        display_name="Basic Asset Template",
        description="Template for creating basic assets",
        base_custom_type_name="simple_asset",
        defaults={
            "resource_name": "MyAsset"
            # No custom_attributes for now
        },
    )

    print(f"✓ Created template: {simple_template.template_name}")
    print(f"  For custom type: {simple_template.base_custom_type_name}")
    print(f"  Defaults: {simple_template.defaults}")

    return simple_template


def step3_validate_template(template, available_types):
    """Step 3: Validate the template."""
    print("\n" + "=" * 50)
    print("STEP 3: Validating template")
    print("=" * 50)

    result = validate_template(template, available_types)

    if result.is_valid:
        print("✓ Template is valid!")
    else:
        print("✗ Template validation failed:")
        for error in result.errors:
            print(f"  Error: {error}")
        for warning in result.warnings:
            print(f"  Warning: {warning}")

    return result


def step4_create_resource(template, available_types):
    """Step 4: Create a resource from the template."""
    print("\n" + "=" * 50)
    print("STEP 4: Creating resource from template")
    print("=" * 50)

    # Simple creation request
    request = TemplateCreateRequest(
        template_name="basic_asset_template",
        resource_name="MyFirstAsset",
        overrides={},  # No overrides for now
    )

    try:
        resource_def = create_resource_from_template(
            template=template, request=request, available_custom_types=available_types
        )

        print(f"✓ Created resource: {resource_def.resource_name}")
        print(f"  Resource class: {resource_def.resource_class}")
        print(f"  Base type: {resource_def.base_type}")
        print(f"  Type: {type(resource_def).__name__}")

        return resource_def

    except Exception as e:
        print(f"✗ Error creating resource: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_simple_examples():
    """Run the simplest possible examples step by step."""
    print("Simple ResourceTemplate System Examples")
    print("Working up from the most basic case...")

    # Step 1: Create minimal custom type
    custom_type = step1_minimal_custom_type()

    # Step 2: Create simple template
    template = step2_simple_template(custom_type)

    # Step 3: Setup available types
    available_types: Dict[str, CustomResourceTypes] = {"simple_asset": custom_type}

    # Step 4: Validate template
    validation_result = step3_validate_template(template, available_types)

    # Step 5: If valid, try to create resource
    if validation_result.is_valid:
        resource = step4_create_resource(template, available_types)

        if resource:
            print("\n" + "=" * 50)
            print("SUCCESS! 🎉")
            print("=" * 50)
            print("We successfully created a resource from a template!")
            print(f"Resource: {resource.resource_name}")
            print(f"From template: {template.template_name}")
            print(f"Using custom type: {custom_type.type_name}")

    print("\n" + "=" * 50)
    print("Simple examples completed!")
    print("=" * 50)


if __name__ == "__main__":
    run_simple_examples()
