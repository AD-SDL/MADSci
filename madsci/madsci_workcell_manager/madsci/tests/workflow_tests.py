from madsci.common.types.workflow_types import WorkflowDefinition
import requests
from pathlib import Path
def test_send_workflow(workflow: str, parameters: dict):
    workflow = WorkflowDefinition.from_yaml(workflow)
    WorkflowDefinition.model_validate(workflow)
    url = f"http://localhost:8013/start_workflow"
    response = requests.post(
        url,
        data={
            "workflow": workflow.model_dump_json(),
            "parameters":{}
            },
        files=[]
        )
    print("hi")
    print(response)
    
test_send_workflow(Path("../../../../tests/example/workflows/test_workflow.workflow.yaml").resolve(), {})