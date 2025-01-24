"""Basic tests for workflow functionality"""

from pathlib import Path

from madsci.client.event_client import default_logger
from madsci.client.workcell_client import WorkcellClient

client = WorkcellClient("http://localhost:8013")

default_logger.log_info(client.get_node("liquid_handler"))
default_logger.log_info(
    client.add_node("liquid_handler", "http://localhost:2000", permanent=True)
)
wf = client.start_workflow(
    Path("../../../../tests/example/workflows/test_workflow.workflow.yaml").resolve(),
    {},
)
default_logger.log_info(wf.workflow_id)
client.resubmit_workflow(wf.workflow_id)
default_logger.log_info(client.get_all_workflows())
