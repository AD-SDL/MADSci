from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.madsci_client.madsci.client.workflow.workflow_client import WorkflowClient
import requests
from pathlib import Path


client = WorkflowClient("http://localhost:8013")
client.send_workflow(Path("../../../../tests/example/workflows/test_workflow.workflow.yaml").resolve(), {})