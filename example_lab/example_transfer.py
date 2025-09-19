"""Run example transfer workflows to demonstrate the functionality."""

from madsci.client.location_client import LocationClient
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.resource_types import Resource

# * Initialize clients for location, workcell, and resource managers
location_client = LocationClient("http://localhost:8006")
workcell_client = WorkcellClient("http://localhost:8005")
resource_client = ResourceClient("http://localhost:8003")

# * Create a demo resource (a plate)
demo_plate = Resource(resource_name="Demo Plate")
demo_plate = resource_client.add_resource(demo_plate)

# * Add the resource to the storage_rack location
l1_deck1 = location_client.get_location_by_name("liquidhandler_1.deck_1")
resource_client.push(l1_deck1.resource_id, demo_plate.resource_id)

# * Run the simple transfer workflow
try:
    result = workcell_client.start_workflow(
        workflow_definition="workflows/simple_transfer.workflow.yaml",
        await_completion=True,
        prompt_on_error=False,
        raise_on_failed=True,
    )
except Exception:
    raise
finally:
    # * Cleanup the demo resource
    resource_client.remove(demo_plate.resource_id)
