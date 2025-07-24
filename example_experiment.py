from madsci.client.experiment_application import ExperimentApplication, ExperimentDesign
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.common.types.step_types import StepDefinition
from madsci.common.types.context_types import MadsciContext

from pydantic import AnyUrl

import datetime

from madsci.client.workcell_client import WorkcellClient

class ExampleExperimentApplication(ExperimentApplication):
    url = "http://localhost:8002/"
    experiment_design = ExperimentDesign(
        experiment_name="Example Experiment",
        experiment_description="Example Experiment - multi-node workflow test.")
                           

def main() -> None:
    """
    Run an example experiment application.
    """
    example_app = ExampleExperimentApplication()

    workflow_def = WorkflowDefinition(
        name="Example Workflow",
        steps=[
            StepDefinition(
                name="Get Liquidhandler Status",
                description=None,
                node="liquidhandler_1",
                action="run_command",
                args={"command": "get_status"},
            ),
	        StepDefinition(
                name="Read Plate",
                description=None,
                node="platereader_1",
                action="read_plate",
                args={},
            ),
            StepDefinition(
                name="Transfer",
                description=None,
                node="robotarm_1",
                action="transfer",
                locations={
                    "source":"location_1",
                    "target":"location_2",
                }
            )
        ]
    )

    with example_app.manage_experiment(
            run_name="Example Run: " + datetime.datetime.now().isoformat(),
            run_description="Example workflow run for testing.",
    ):
        example_app.workcell_client.start_workflow(workflow_def)

    # ctx = MadsciContext()
    # print(ctx.lab_server_url)  # http://localhost:8000/
    # print(ctx.workcell_server_url)  # http://localhost:8005/

    

if __name__ == "__main__":
    main()