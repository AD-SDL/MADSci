from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.madsci_client.madsci.client.workcell.workcell_client import WorkcellClient
import requests
from pathlib import Path


client = WorkcellClient("http://localhost:8013")

print(client.get_node("liquid_handler"))
print(client.add_node("liquid_handler", "http://localhost:2000", permanent=True))
wf = client.start_workflow(Path("../../../../tests/example/workflows/test_workflow.workflow.yaml").resolve(), {})
print(wf.workflow_id)
client.resubmit_workflow(wf.workflow_id)
print(client.get_all_workflows())