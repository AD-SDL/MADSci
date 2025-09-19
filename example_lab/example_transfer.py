"""Run example transfer workflows to demonstrate the functionality."""

from madsci.client.location_client import LocationClient
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.resource_types import Resource
from rich import print

# * Initialize clients for location, workcell, and resource managers
location_client = LocationClient("http://localhost:8006")
workcell_client = WorkcellClient("http://localhost:8005")
resource_client = ResourceClient("http://localhost:8003")

print("=== Running Simple Transfer Workflow ===")

# * Create a demo resource (a plate) for simple transfer
demo_plate_1 = Resource(resource_name="Demo Plate 1")
demo_plate_1 = resource_client.add_resource(demo_plate_1)

# * Add the resource to liquidhandler_1.deck_1 for simple transfer
l1_deck1 = location_client.get_location_by_name("liquidhandler_1.deck_1")
resource_client.push(l1_deck1.resource_id, demo_plate_1.resource_id)

# * Run the simple transfer workflow
try:
    print("Starting simple transfer workflow...")
    result = workcell_client.start_workflow(
        workflow_definition="workflows/simple_transfer.workflow.yaml",
        await_completion=True,
        prompt_on_error=False,
        raise_on_failed=True,
    )
    print("Simple transfer workflow completed successfully!")
except Exception as e:
    print(f"Simple transfer workflow failed: {e}")
    raise
finally:
    # * Cleanup the demo resource
    resource_client.remove(demo_plate_1.resource_id)

print("\n=== Running Multistep Transfer Workflow ===")

# * Create a demo resource (a plate) for multistep transfer
demo_plate_2 = Resource(resource_name="Demo Plate 2")
demo_plate_2 = resource_client.add_resource(demo_plate_2)

# * Add the resource to storage_rack for multistep transfer
storage_rack = location_client.get_location_by_name("storage_rack")
resource_client.push(storage_rack.resource_id, demo_plate_2.resource_id)

# * Run the multistep transfer workflow
try:
    print("Starting multistep transfer workflow...")
    result = workcell_client.start_workflow(
        workflow_definition="workflows/multistep_transfer.workflow.yaml",
        await_completion=True,
        prompt_on_error=False,
        raise_on_failed=True,
    )
    print("Multistep transfer workflow completed successfully!")
    print(
        "Resource has completed the full journey: storage_rack -> liquidhandler_1.deck_2 -> platereader_1.plate_carriage -> storage_rack"
    )
except Exception as e:
    print(f"Multistep transfer workflow failed: {e}")
    raise
finally:
    # * Cleanup the demo resource
    resource_client.remove(demo_plate_2.resource_id)

print("\n=== All transfer workflows completed successfully! ===")
