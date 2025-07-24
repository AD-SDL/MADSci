"""An Example Application"""

from madsci.client.experiment_application import ExperimentApplication
from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.step_types import StepDefinition
from madsci.common.types.node_types import NodeDefinition, RestNodeConfig
from madsci.common.types.workflow_types import WorkflowDefinition
from pydantic import AnyUrl
import datetime

class ExampleApp(ExperimentApplication):
    """An Example Application"""

    experiment_design = ExperimentDesign(
        experiment_name="Example Experiment",
        experiment_description="Example Experiment - multi-node workflow test.",
        node_config=RestNodeConfig(node_url=AnyUrl("http://localhost:6000")))
    
    inputs = [
        {"name": "test", "default": "foo"},
        {"name": "test2", "default": "bar"},
        {"name": "test3", "default": 42},]
    
    def run_experiment(self, test: str, test2: str, test3: int) -> str:
        """main experiment function"""
        return "test" + test + test2 + str(test3)

def main() -> None:
    """
    Run an example experiment application.
    """
    example_app = ExampleApp()

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
    # example_app.workcell_client.add_node(
    #         node_name="example_app_node",
    #         node_url="http://localhost:6000",
    #         node_description="My experiment app node",
    #     )
    example_app.start_app()
    
    # with example_app.manage_experiment(
    #         run_name="Example Run: " + datetime.datetime.now().isoformat(),
    #         run_description="Example workflow run for testing.",
    # ):
    #     example_app.workcell_client.start_workflow(workflow_def)


if __name__ == "__main__":
    main()
