"""Provides an ExperimentApplication class that manages the execution of an experiment."""

from typing import Optional

from madsci.client.event_client import EventClient
from madsci.client.experiment_client import ExperimentClient
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentDesign,
)
from pydantic import AnyUrl


class ExperimentApplication:
    """
    An experiment application that helps manage the execution of an experiment.

    You can either use this class as a base class for your own application class, or create an instance of it to manage the execution of an experiment.
    """

    experiment: Optional[Experiment] = None
    experiment_design: Optional[ExperimentDesign] = None
    logger = EventClient()

    def __init__(
        self,
        url: AnyUrl,
        experiment_design: Optional[ExperimentDesign] = None,
        experiment: Optional[Experiment] = None,
    ) -> "ExperimentApplication":
        """Initialize the experiment application. You can provide an experiment design to use for creating new experiments, or an existing experiment to continue."""
        self.url = AnyUrl(url)
        self.experiment_design = experiment_design
        self.experiment = experiment
        self.experiment_client = ExperimentClient(url=self.url)
        if self.experiment_design.event_client_config:
            self.logger = EventClient(config=self.experiment_design.event_client_config)

    @classmethod
    def start_new(
        cls, url: AnyUrl, experiment_design: ExperimentDesign
    ) -> "ExperimentApplication":
        """Create a new experiment application with a new experiment."""
        self = cls(url=url, experiment_design=experiment_design)
        self.start_experiment()
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

    def start_experiment(self) -> None:
        """Start the experiment."""
        try:
            self.experiment_client.get_experiment_design(
                experiment_design_id=self.experiment_design.experiment_design_id
            )
            self.experiment_client.update_experiment_design(
                experiment_design=self.experiment_design
            )
        except Exception:
            self.experiment_design = self.experiment_client.register_experiment_design(
                experiment_design=self.experiment_design
            )
        self.experiment = self.experiment_client.start_experiment(
            experiment_design=self.experiment_design
        )

    def end_experiment(self) -> None:
        """End the experiment."""
        self.experiment = self.experiment_client.end_experiment(
            experiment_id=self.experiment.experiment_id
        )
