"""Client for the MADSci Experiment Manager."""

from typing import Optional, Union

import requests
from madsci.common.types.auth_types import OwnershipInfo
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

    def __init__(
        self, url: Union[str, AnyUrl], ownership_info: Optional[OwnershipInfo] = None
    ) -> "ExperimentClient":
        """Create a new Experiment Client."""
        self.url = AnyUrl(url)
        self.ownership_info = ownership_info if ownership_info else OwnershipInfo()

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

    def start_experiment(
        self,
        experiment_design: ExperimentDesign,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
    ) -> Experiment:
        """Start an experiment based on an ExperimentDesign."""
        response = requests.post(
            f"{self.url}/experiment",
            json={
                "experiment_design": experiment_design,
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
