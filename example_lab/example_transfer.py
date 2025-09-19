"""Run example transfer workflow with dynamic location querying.

Creates a demo resource, places it in storage, and runs a workflow that:
1. Transfers the resource to robot station 1
2. Waits briefly for processing simulation
3. Transfers all contents from robot station to hybrid station
"""

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
storage_rack = location_client.get_location_by_name("storage_rack")
resource_client.push(storage_rack.resource_id, demo_plate.resource_id)

# * Query location IDs dynamically
robot_station_1 = location_client.get_location_by_name("robot_station_1")
hybrid_station = location_client.get_location_by_name("hybrid_station")

# * Run the simple transfer workflow
try:
    result = workcell_client.start_workflow(
        workflow_definition="workflows/simple_transfer.workflow.yaml",
        json_inputs={
            "test_resource_id": demo_plate.resource_id,
            "robot_station_1_id": robot_station_1.location_id,
            "hybrid_station_id": hybrid_station.location_id,
        },
        await_completion=True,
        prompt_on_error=False,
        raise_on_failed=True,
    )
except Exception:
    raise
finally:
    # * Cleanup the demo resource
    resource_client.remove(demo_plate.resource_id)
