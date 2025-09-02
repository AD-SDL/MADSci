"""An Example Application"""

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.node_types import NodeDefinition
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from pydantic import AnyUrl


class ExampleApp(ExperimentApplication):
    """An Example Application"""

    experiment_design = ExperimentDesign(
        experiment_name="Example_App",
    )
    config = ExperimentApplicationConfig(node_url=AnyUrl("http://localhost:6000"))

    def run_experiment(self) -> str:
        """main experiment function"""

        self.workcell_client.submit_workflow(
            "./workflows/test_feedforward_data.workflow.yaml",
            input_values={"test_command_1": "test"},
            input_files={"test_file_2": "./test.txt"},
        )
        return "test"


if __name__ == "__main__":
    app = ExampleApp(
        node_definition=NodeDefinition(
            node_name="example_app", module_name="example_app"
        )
    )
    app.start_app()
