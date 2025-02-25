"""Provides an ExperimentApplication class that manages the execution of an experiment."""

import time
from contextlib import contextmanager
from typing import Optional

from madsci.client.event_client import EventClient
from madsci.client.experiment_client import ExperimentClient
from madsci.common.exceptions import ExperimentCancelledError, ExperimentFailedError
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
    ExperimentStatus,
)
from madsci.common.utils import threaded_daemon
from pydantic import AnyUrl


class ExperimentApplication:
    """
    An experiment application that helps manage the execution of an experiment.

    You can either use this class as a base class for your own application class, or create an instance of it to manage the execution of an experiment.
    """

    experiment: Optional[Experiment] = None
    """The current experiment being run."""
    experiment_design: Optional[ExperimentDesign] = None
    """The design of the experiment."""
    url: AnyUrl = AnyUrl("http://localhost:8002")
    """The URL of the experiment manager server."""
    logger = EventClient()
    """The event logger for the experiment."""

    def __init__(
        self,
        url: Optional[AnyUrl] = None,
        experiment_design: Optional[ExperimentDesign] = None,
        experiment: Optional[Experiment] = None,
    ) -> "ExperimentApplication":
        """Initialize the experiment application. You can provide an experiment design to use for creating new experiments, or an existing experiment to continue."""
        self.url = AnyUrl(url) if url else self.url
        self.experiment_design = (
            experiment_design if experiment_design else self.experiment_design
        )
        self.experiment = experiment if experiment else self.experiment

        self.experiment_client = ExperimentClient(url=self.url)
        if self.experiment_design and self.experiment_design.event_client_config:
            self.logger = EventClient(config=self.experiment_design.event_client_config)

    @classmethod
    def start_new(
        cls, url: AnyUrl, experiment_design: ExperimentDesign
    ) -> "ExperimentApplication":
        """Create a new experiment application with a new experiment."""
        self = cls(url=url, experiment_design=experiment_design)
        self.start_experiment_run()
        return self

    @classmethod
    def continue_experiment(
        cls, url: AnyUrl, experiment: Experiment
    ) -> "ExperimentApplication":
        """Create a new experiment application with an existing experiment."""
        self = cls(url=url, experiment=experiment)
        self.experiment_client.continue_experiment(
            experiment_id=experiment.experiment_id
        )
        return self

    def start_experiment_run(
        self, run_name: Optional[str] = None, run_description: Optional[str] = None
    ) -> None:
        """Sends the ExperimentDesign to the server to register a new experimental run."""
        self.experiment = self.experiment_client.start_experiment(
            experiment_design=self.experiment_design,
            run_name=run_name,
            run_description=run_description,
        )
        self.logger.log_info(
            f"Started run '{self.experiment.run_name}' ({self.experiment.experiment_id}) of experiment '{self.experiment.experiment_design.experiment_name}'"
        )

    def end_experiment(self, status: Optional[ExperimentStatus] = None) -> None:
        """End the experiment."""
        self.experiment = self.experiment_client.end_experiment(
            experiment_id=self.experiment.experiment_id,
            status=status,
        )
        self.logger.log_info(
            f"Ended run '{self.experiment.run_name}' ({self.experiment.experiment_id}) of experiment '{self.experiment.experiment_design.experiment_name}'"
        )

    def pause_experiment(self) -> None:
        """Pause the experiment."""
        self.experiment = self.experiment_client.pause_experiment(
            experiment_id=self.experiment.experiment_id
        )
        self.logger.log_info(
            f"Paused run '{self.experiment.run_name}' ({self.experiment.experiment_id}) of experiment '{self.experiment.experiment_design.experiment_name}'"
        )

    def cancel_experiment(self) -> None:
        """Cancel the experiment."""
        self.experiment = self.experiment_client.cancel_experiment(
            experiment_id=self.experiment.experiment_id
        )
        self.logger.log_info(
            f"Cancelled run '{self.experiment.run_name}' ({self.experiment.experiment_id}) of experiment '{self.experiment.experiment_design.experiment_name}'"
        )

    def fail_experiment(self) -> None:
        """Fail the experiment."""
        self.experiment = self.experiment_client.end_experiment(
            experiment_id=self.experiment.experiment_id,
            status=ExperimentStatus.FAILED,
        )
        self.logger.log_info(
            f"Failed run '{self.experiment.run_name}' ({self.experiment.experiment_id}) of experiment '{self.experiment.experiment_design.experiment_name}'"
        )

    @contextmanager
    def manage_experiment(
        self, run_name: Optional[str] = None, run_description: Optional[str] = None
    ) -> contextmanager:
        """Context manager to start and end an experiment."""
        self.start_experiment_run(run_name=run_name, run_description=run_description)
        try:
            yield
        finally:
            self.end_experiment()

    @threaded_daemon
    def loop(self) -> None:
        """Function that runs the experimental loop. This should be overridden by subclasses."""
        raise NotImplementedError

    def check_experiment_status(self) -> None:
        """
        Update and check the status of the current experiment.

        Raises an exception if the experiment has been cancelled or failed.
        If the experiment has been paused, this function will wait until the experiment is resumed.

        Raises:
            ExperimentCancelledError: If the experiment has been cancelled.
            ExperimentFailedError: If the experiment has failed.
        """
        self.experiment = self.experiment_client.get_experiment(
            experiment_id=self.experiment.experiment_id
        )
        exception = None
        if self.experiment.status == ExperimentStatus.PAUSED:
            self.logger.log_warning(
                f"Experiment '{self.experiment.experiment_design.experiment_name}' has been paused."
            )
            while True:
                time.sleep(5)
                self.experiment = self.experiment_client.get_experiment(
                    experiment_id=self.experiment.experiment_id
                )
                if self.experiment.status != ExperimentStatus.PAUSED:
                    break
        if self.experiment.status == ExperimentStatus.CANCELLED:
            exception = ExperimentCancelledError(
                "Experiment manager reports that the experiment has been cancelled."
            )
        elif self.experiment.status == ExperimentStatus.FAILED:
            exception = ExperimentFailedError(
                "Experiment manager reports that the experiment has failed."
            )

        if exception:
            self.logger.log_error(exception.message)
            raise exception


if __name__ == "__main__":
    import datetime

    class MyExperimentApplication(ExperimentApplication):
        """An example experiment application."""

        experiment_design = ExperimentDesign(
            experiment_name="My Example Experiment",
            experiment_description="An example experimental design",
        )
        url = "http://localhost:8002"

        def loop(self, iterations: int = 10) -> None:
            """Run the experiment loop."""
            for i in range(iterations):
                time.sleep(10)
                self.check_experiment_status()
                self.logger.log_info(f"Running experiment loop {i}")

    experiment_app = MyExperimentApplication()
    current_time = datetime.datetime.now()
    with experiment_app.manage_experiment(
        run_name=f"My Experiment Run {current_time}",
        run_description=f"Run for my example experiment, started at ~{current_time}",
    ):
        experiment_app.loop(iterations=10)
