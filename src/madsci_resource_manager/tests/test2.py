"""
Simple comparison of creating PF400 gripper using templates vs direct creation.
"""
# flake8: noqa

# Import for template method

# Generate node ID
import ulid

# Import for direct method
from madsci.common.types.resource_types.definitions import (
    CustomResourceAttributeDefinition,
    OwnershipInfo,
    SlotResourceDefinition,
)
from madsci.common.types.resource_types.templates import (
    create_resource_from_template,
    get_template_info,
)

node_ulid = str(ulid.ULID())

node_name = "main_lab_node"

print("PF400 GRIPPER CREATION COMPARISON")
print("=" * 50)

# First, let's see what the template looks like
print("\nTEMPLATE INFO:")
template_info = get_template_info("pf400_gripper")
if template_info:
    print(f"Display Name: {template_info['display_name']}")
    print(f"Description: {template_info['description']}")
    # print(f"Required Fields: {template_info['required_overrides']}")

# METHOD 1: Template System (simple version)
print("\nMETHOD 1: Using Template (no custom attributes)")
try:
    pf400_template = create_resource_from_template(
        template_name="pf400_gripper",
        resource_name="pf400_gripper_template",
        owner=OwnershipInfo(node_id=node_ulid),
        resource_name_prefix="TEST",
    )
    print(pf400_template)
    # print(f"Resource Name: {pf400_template.resource_name}")
    # print(f"Base Type: {pf400_template.base_type}")
    # print(f"Owner: {pf400_template.owner.node_id}")
    # print("SUCCESS: Template created")

except Exception as e:
    print(f"Template failed: {e}")

# METHOD 2: Direct Creation
print("\nMETHOD 2: Direct SlotResourceDefinition")
try:
    pf400_direct = SlotResourceDefinition(
        resource_name="pf400_gripper_" + str(node_name),
        owner=OwnershipInfo(node_id=node_ulid),
        custom_attributes=[
            CustomResourceAttributeDefinition(
                attribute_name="robot_type", default_value="PF400"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="manufacturer", default_value="Precise Automation"
            ),
            CustomResourceAttributeDefinition(
                attribute_name="gripper_type", default_value="parallel_jaw"
            ),
        ],
    )
    print(pf400_direct)
    # print(f"Resource Name: {pf400_direct.resource_name}")
    # print(f"Base Type: {pf400_direct.base_type}")
    # print(f"Owner: {pf400_direct.owner.node_id}")
    # print("Custom Attributes:")
    # for attr in pf400_direct.custom_attributes:
    #     print(f"  {attr.attribute_name}: {attr.default_value}")
    # print("SUCCESS: Direct creation")

except Exception as e:
    print(f"Direct method failed: {e}")
