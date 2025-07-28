"""An Example Application"""

from madsci.client.experiment_application import ExperimentApplication
from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.node_types import NodeDefinition, RestNodeConfig
from pydantic import AnyUrl


class ExampleApp(ExperimentApplication):
    """An Example Application"""

    experiment_design = ExperimentDesign(
        experiment_name="Example_App",
        node_config=RestNodeConfig(node_url=AnyUrl("http://localhost:6000")),
    )

    def run_experiment(self, test: str, test2: str, test3: int) -> str:
        """main experiment function"""
        return "test" + test + test2 + str(test3)


if __name__ == "__main__":
    app = ExampleApp(
        node_definition=NodeDefinition(
            node_name="example_app", module_name="example_app"
        )
    )
    app.start_app()
