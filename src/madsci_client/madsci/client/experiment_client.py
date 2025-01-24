"""Client for the MADSci Experiment Manager."""

from pathlib import Path
from typing import Any, Optional, Union

import requests
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentalCampaign,
    ExperimentDesign,
)
from pydantic import AnyUrl
from ulid import ULID


class ExperimentClient:
    """Client for the MADSci Experiment Manager."""

    url: AnyUrl

    def __init__(self, url: Union[str, AnyUrl]) -> "ExperimentClient":
        """Create a new Experiment Client."""
        self.url = AnyUrl(url)

    def register_experiment_design(
        self, experiment_design: Union[ExperimentDesign, dict[str, Any], str, Path]
    ) -> ExperimentDesign:
        """Register an experiment with the Experiment Manager."""
        if isinstance(experiment_design, dict):
            experiment_design = ExperimentDesign.model_validate(experiment_design)
        elif isinstance(experiment_design, (Path, str)):
            experiment_design = ExperimentDesign.from_yaml(experiment_design)
        response = requests.post(
            f"{self.url}/experiment_design",
            json=experiment_design.model_dump(mode="json"),
            timeout=10,
        )
        if not response.ok:
            response.raise_for_status()
        return ExperimentDesign.model_validate(response.json())

    def get_experiment(self, experiment_id: Union[str, ULID]) -> dict:
        """Get an experiment by ID."""
        response = requests.get(f"{self.url}/experiment/{experiment_id}", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def get_experiments(self, number: int = 10) -> list[Experiment]:
        """Get a list of the latest experiments."""
        response = requests.get(
            f"{self.url}/experiments", params={number: number}, timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        return [Experiment.model_validate(experiment) for experiment in response.json()]

    def get_experiment_design(self, experiment_design_id: str) -> ExperimentDesign:
        """Get an experiment design by ID."""
        response = requests.get(
            f"{self.url}/experiment_design/{experiment_design_id}", timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        return ExperimentDesign.model_validate(response.json())

    def get_experiment_designs(self, number: int = 10) -> list[ExperimentDesign]:
        """Get a list of the latest experiment designs."""
        response = requests.get(
            f"{self.url}/experiment_designs", params={number: number}, timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        return [
            ExperimentDesign.model_validate(experiment_design)
            for experiment_design in response.json()
        ]

    def start_experiment(
        self,
        experiment_design_id: str,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
    ) -> Experiment:
        """Start an experiment based on an ExperimentDesign."""
        response = requests.post(
            f"{self.url}/experiment",
            json={
                "experiment_design_id": experiment_design_id,
                "run_name": run_name,
                "run_description": run_description,
            },
            timeout=10,
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def end_experiment(self, experiment_id: Union[str, ULID]) -> Experiment:
        """End an experiment by ID."""
        response = requests.post(
            f"{self.url}/experiment/{experiment_id}/end", timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def register_campaign(self, campaign: ExperimentalCampaign) -> ExperimentalCampaign:
        """Register a new experimental campaign."""
        response = requests.post(f"{self.url}/campaign", json=campaign, timeout=10)
        if not response.ok:
            response.raise_for_status()
        return response.json()

    def get_campaign(self, campaign_id: str) -> ExperimentalCampaign:
        """Get an experimental campaign by ID."""
        response = requests.get(f"{self.url}/campaign/{campaign_id}", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return response.json()
