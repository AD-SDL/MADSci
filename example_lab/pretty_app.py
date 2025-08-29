"""An Example Application"""

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.node_types import NodeDefinition
from madsci.experiment_application import ExperimentApplication


def run_calculation(input: int) -> int:
    """runs a calculation"""
    return input + 1


class ExampleApp(ExperimentApplication):
    """An Example Application"""

    experiment_design = ExperimentDesign(experiment_name="Example_App")

    def run_experiment(self) -> str:
        """main experiment function"""
        calculated_value = 0
        while calculated_value < 3:
            print(self.workcell_client.get_nodes())

            workflow = self.workcell_client.submit_workflow(
                "./workflows/example_workflow.workflow.yaml",
                parameters={"example_parameter": 2},
            )

            datapoint = self.data_client.get_datapoint(
                workflow.get_datapoint_id_by_label("example_file")
            )
            measured_value = datapoint.value
            calculated_value = run_calculation(measured_value)
        return calculated_value


if __name__ == "__main__":
    app = ExampleApp(
        node_definition=NodeDefinition(
            node_name="example_app", module_name="example_app"
        )
    )
    app.run_experiment()
