import datetime
import time
from madsci.client.experiment_application import ExperimentApplication, ExperimentDesign
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.client.event_client import EventClient

class TestApp(ExperimentApplication):
    url = "http://localhost:8002/"
    experiment_design = ExperimentDesign(
        experiment_name="Fixed Status Test",
        experiment_description="Testing the status fix",
    )

app = TestApp()
workflow = WorkflowDefinition(
    name="Status Test Workflow",
    steps=[{
        "name": "Test Step",
        "node": "liquidhandler_1",
        "action": "run_command",
        "args": {"command": "test_command"},
    }]
)

with app.manage_experiment(
    run_name=f"status_test_{datetime.datetime.now().strftime('%H%M%S')}",
    run_description="Testing the status fix",
):
    app.workcell_client.start_workflow(workflow)
    time.sleep(3)

# Check results
client = EventClient(event_server_url="http://localhost:8001")
summary = client.get_utilization_summary()

print("🎯 Results after status fix:")
print(f"System: {summary.system_utilization.utilization_percentage:.1f}%")
for node_id, node_util in summary.node_utilizations.items():
    print(f"Node {node_id}: {node_util.utilization_percentage:.1f}% ({node_util.current_state})")
    print(f"  Busy time: {node_util.busy_time:.1f}s")
    print(f"  Active actions: {len(node_util.active_actions)}")