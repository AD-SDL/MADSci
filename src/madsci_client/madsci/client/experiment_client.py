"""Client for the MADSci Experiment Manager."""

from typing import Optional, Union

import requests
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentalCampaign,
    ExperimentDesign,
    ExperimentRegistration,
    ExperimentStatus,
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
        try:
            server_def = requests.get(str(self.url) + "definition", timeout=10).json()
            self.workcell_client = WorkcellClient(server_def["workcell_manager_url"])
            self.resource_client = ResourceClient(server_def["resource_manager_url"])
        except Exception as e:
            raise e

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
            json=ExperimentRegistration(
                experiment_design=experiment_design.model_dump(mode="json"),
                run_name=run_name,
                run_description=run_description,
            ).model_dump(mode="json"),
            timeout=10,
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def end_experiment(
        self, experiment_id: Union[str, ULID], status: Optional[ExperimentStatus] = None
    ) -> Experiment:
        """End an experiment by ID. Optionally, set the status."""
        response = requests.post(
            f"{self.url}/experiment/{experiment_id}/end",
            params={"status": status},
            timeout=10,
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def continue_experiment(self, experiment_id: Union[str, ULID]) -> Experiment:
        """Continue an experiment by ID."""
        response = requests.post(
            f"{self.url}/experiment/{experiment_id}/continue", timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def pause_experiment(self, experiment_id: Union[str, ULID]) -> Experiment:
        """Pause an experiment by ID."""
        response = requests.post(
            f"{self.url}/experiment/{experiment_id}/pause", timeout=10
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def cancel_experiment(self, experiment_id: Union[str, ULID]) -> Experiment:
        """Cancel an experiment by ID."""
        response = requests.post(
            f"{self.url}/experiment/{experiment_id}/cancel", timeout=10
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
