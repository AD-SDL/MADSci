"""Client for the MADSci Experiment Manager."""

from typing import Optional, Union

from madsci.common.context import get_current_madsci_context
from madsci.common.types.client_types import ExperimentClientConfig
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentalCampaign,
    ExperimentDesign,
    ExperimentRegistration,
    ExperimentStatus,
)
from madsci.common.utils import create_http_session
from pydantic import AnyUrl
from ulid import ULID


class ExperimentClient:
    """Client for the MADSci Experiment Manager."""

    experiment_server_url: AnyUrl

    def __init__(
        self,
        experiment_server_url: Optional[Union[str, AnyUrl]] = None,
        config: Optional[ExperimentClientConfig] = None,
    ) -> "ExperimentClient":
        """
        Create a new Experiment Client.

        Args:
            experiment_server_url: The URL of the experiment server. If not provided, will use the URL from the current MADSci context.
            config: Client configuration for retry and timeout settings. If not provided, uses default ExperimentClientConfig.
        """
        self.experiment_server_url = (
            AnyUrl(experiment_server_url)
            if experiment_server_url
            else get_current_madsci_context().experiment_server_url
        )
        if not self.experiment_server_url:
            raise ValueError(
                "No experiment server URL provided, please specify a URL or set the context."
            )

        # Store config and create session
        self.config = config if config is not None else ExperimentClientConfig()
        self.session = create_http_session(config=self.config)

    def get_experiment(
        self, experiment_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> dict:
        """
        Get an experiment by ID.

        Args:
            experiment_id: The ID of the experiment to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.experiment_server_url}experiment/{experiment_id}",
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def get_experiments(
        self, number: int = 10, timeout: Optional[float] = None
    ) -> list[Experiment]:
        """
        Get a list of the latest experiments.

        Args:
            number: Number of experiments to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.experiment_server_url}experiments",
            params={"number": number},
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return [Experiment.model_validate(experiment) for experiment in response.json()]

    def start_experiment(
        self,
        experiment_design: ExperimentDesign,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Experiment:
        """
        Start an experiment based on an ExperimentDesign.

        Args:
            experiment_design: The design of the experiment to start.
            run_name: Optional name for the experiment run.
            run_description: Optional description for the experiment run.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.post(
            f"{self.experiment_server_url}experiment",
            json=ExperimentRegistration(
                experiment_design=experiment_design.model_dump(mode="json"),
                run_name=run_name,
                run_description=run_description,
            ).model_dump(mode="json"),
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def end_experiment(
        self,
        experiment_id: Union[str, ULID],
        status: Optional[ExperimentStatus] = None,
        timeout: Optional[float] = None,
    ) -> Experiment:
        """
        End an experiment by ID. Optionally, set the status.

        Args:
            experiment_id: The ID of the experiment to end.
            status: Optional status to set on the experiment.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.post(
            f"{self.experiment_server_url}experiment/{experiment_id}/end",
            params={"status": status},
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def continue_experiment(
        self, experiment_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> Experiment:
        """
        Continue an experiment by ID.

        Args:
            experiment_id: The ID of the experiment to continue.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.post(
            f"{self.experiment_server_url}experiment/{experiment_id}/continue",
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def pause_experiment(
        self, experiment_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> Experiment:
        """
        Pause an experiment by ID.

        Args:
            experiment_id: The ID of the experiment to pause.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.post(
            f"{self.experiment_server_url}experiment/{experiment_id}/pause",
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def cancel_experiment(
        self, experiment_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> Experiment:
        """
        Cancel an experiment by ID.

        Args:
            experiment_id: The ID of the experiment to cancel.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.post(
            f"{self.experiment_server_url}experiment/{experiment_id}/cancel",
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return Experiment.model_validate(response.json())

    def register_campaign(
        self, campaign: ExperimentalCampaign, timeout: Optional[float] = None
    ) -> ExperimentalCampaign:
        """
        Register a new experimental campaign.

        Args:
            campaign: The campaign to register.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.post(
            f"{self.experiment_server_url}campaign",
            json=campaign.model_dump(mode="json"),
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return response.json()

    def get_campaign(
        self, campaign_id: str, timeout: Optional[float] = None
    ) -> ExperimentalCampaign:
        """
        Get an experimental campaign by ID.

        Args:
            campaign_id: The ID of the campaign to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.experiment_server_url}campaign/{campaign_id}",
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return response.json()
