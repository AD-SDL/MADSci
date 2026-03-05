"""Example experiment using MADSci ExperimentTUI.

This demonstrates an interactive terminal UI experiment that:
1. Launches a Textual-based TUI with status display, log viewer, and controls
2. Sets up resources (plate) in the correct locations
3. Runs a workflow loop (liquid handler -> plate reader) until a
   measurement target is reached
4. Supports interactive pause/cancel via the TUI controls

The TUI provides:
- Start/Pause/Cancel/Quit buttons
- Keyboard shortcuts (s=Start, p=Pause, c=Cancel, q=Quit, r=Refresh)
- Real-time status display and log viewer

Usage:
    python example_experiment_tui.py

Requires the Example Lab to be running (see README or run `just up`).
Requires the `textual` package (`pip install textual`).
"""

import contextlib
from pathlib import Path

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.parameter_types import ParameterInputFile
from madsci.common.types.resource_types import Asset
from madsci.common.types.step_types import StepDefinition
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.experiment_application.experiment_tui import ExperimentTUI

# Protocol file path (relative to this script's location)
PROTOCOL_PATH = Path(__file__).parent / "example_lab" / "protocols" / "protocol.py"

# Define the workflow used by this experiment
WORKFLOW_DEFINITION = WorkflowDefinition(
    name="Example Workflow",
    steps=[
        StepDefinition(
            name="Run Liquidhandler Protocol",
            description="Run the Liquidhandler",
            node="liquidhandler_1",
            action="run_protocol",
            files={
                "protocol": ParameterInputFile(
                    key="protocol",
                    description="the liquid handler protocol file",
                )
            },
        ),
        StepDefinition(
            name="Transfer from liquid handler to plate reader",
            description="Transfer an asset from the liquid handler to the plate reader",
            node="robotarm_1",
            action="transfer",
            locations={
                "source": "liquidhandler_1.deck_1",
                "target": "platereader_1.plate_carriage",
            },
        ),
        StepDefinition(
            name="Run platereader measurement",
            key="measurement",
            description="Measure a well on the plate reader",
            node="platereader_1",
            action="read_well",
        ),
        StepDefinition(
            name="Transfer from plate reader to liquid handler",
            description="Transfer an asset from the plate reader to the liquid handler",
            node="robotarm_1",
            action="transfer",
            locations={
                "source": "platereader_1.plate_carriage",
                "target": "liquidhandler_1.deck_1",
            },
        ),
    ],
)


class ExampleExperimentTUI(ExperimentTUI):
    """An interactive TUI experiment that iterates until a measurement target is reached.

    This is the same experiment logic as ExampleExperiment (in example_experiment.py),
    but using the TUI modality for interactive control. The key difference is the use
    of check_experiment_status() to allow the user to pause or cancel the experiment
    from the TUI.
    """

    experiment_design = ExperimentDesign(
        experiment_name="Example TUI Experiment",
        experiment_description="Interactive TUI experiment that iterates until a measurement threshold is met.",
    )

    def run_experiment(self, desired_limit: float = 12.0) -> dict:
        """Run the experiment loop with TUI support.

        Sets up resources, then repeatedly runs the workflow until the
        platereader measurement drops below the desired limit. Calls
        check_experiment_status() each iteration to allow the user to
        pause or cancel from the TUI.

        Args:
            desired_limit: Stop when the measurement is below this value.

        Returns:
            Dictionary with the final measurement result.
        """
        self._setup_resources()

        measurement = float("inf")
        iteration = 0
        while measurement > desired_limit:
            # Check for pause/cancel requests from the TUI
            self.check_experiment_status()

            iteration += 1
            self.logger.info(
                f"Iteration {iteration}: current={measurement}, target<{desired_limit}"
            )

            workflow = self.workcell_client.start_workflow(
                WORKFLOW_DEFINITION,
                file_inputs={"protocol": PROTOCOL_PATH},
                prompt_on_error=False,
            )
            datapoint = workflow.get_datapoint(step_key="measurement")

            self.data_client.save_datapoint_value(
                datapoint.datapoint_id, ".scratch/measurement.txt"
            )
            with Path(".scratch/measurement.txt").open() as f:
                measurement = float(f.read())
                self.logger.info(f"Platereader result: {measurement}")

        self.logger.info(
            f"Measurement {measurement} is below limit {desired_limit} after {iteration} iterations."
        )
        return {"final_measurement": measurement, "iterations": iteration}

    def _setup_resources(self) -> None:
        """Ensure a plate is in the liquid handler deck before running."""
        asset = self.resource_client.add_resource(Asset(resource_name="well_plate"))

        lh_deck = self.location_client.get_location_by_name("liquidhandler_1.deck_1")
        with contextlib.suppress(Exception):
            self.resource_client.pop(lh_deck.resource_id)

        self.resource_client.push(lh_deck.resource_id, asset.resource_id)

        pr_carriage = self.location_client.get_location_by_name(
            "platereader_1.plate_carriage"
        )
        with contextlib.suppress(Exception):
            self.resource_client.pop(pr_carriage.resource_id)


if __name__ == "__main__":
    ExampleExperimentTUI(
        lab_server_url="http://localhost:8000",
    ).run_tui()
