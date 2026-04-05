"""Client for the MADSci Experiment Manager."""

from __future__ import annotations

from typing import Optional, Union

import httpx
from madsci.client.http import DualModeClientMixin
from madsci.common.context import get_current_madsci_context
from madsci.common.http_client import create_httpx_client
from madsci.common.types.client_types import ExperimentClientConfig
from madsci.common.types.experiment_types import (
    Experiment,
    ExperimentalCampaign,
    ExperimentDesign,
    ExperimentRegistration,
    ExperimentStatus,
)
from pydantic import AnyUrl
from ulid import ULID


class ExperimentClient(DualModeClientMixin):
    """Client for the MADSci Experiment Manager."""

    experiment_server_url: AnyUrl

    def __init__(
        self,
        experiment_server_url: Optional[Union[str, AnyUrl]] = None,
        config: Optional[ExperimentClientConfig] = None,
    ) -> ExperimentClient:
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

        # Store config and create httpx client
        self.config = config if config is not None else ExperimentClientConfig()
        self._client = create_httpx_client(config=self.config)
        self._async_client = None

    @property
    def session(self) -> httpx.Client:
        """Backward-compatible accessor for the underlying HTTP client."""
        return self._client

    # ------------------------------------------------------------------
    # Sync methods
    # ------------------------------------------------------------------

    def get_experiment(
        self, experiment_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> dict:
        """
        Get an experiment by ID.

        Args:
            experiment_id: The ID of the experiment to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self._request(
            "GET",
            f"{self.experiment_server_url}experiment/{experiment_id}",
            timeout=timeout or self.config.timeout_default,
        )
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
        response = self._request(
            "GET",
            f"{self.experiment_server_url}experiments",
            params={"number": number},
            timeout=timeout or self.config.timeout_default,
        )
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
        response = self._request(
            "POST",
            f"{self.experiment_server_url}experiment",
            json=ExperimentRegistration(
                experiment_design=experiment_design.model_dump(mode="json"),
                run_name=run_name,
                run_description=run_description,
            ).model_dump(mode="json"),
            timeout=timeout or self.config.timeout_default,
        )
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
        response = self._request(
            "POST",
            f"{self.experiment_server_url}experiment/{experiment_id}/end",
            params={"status": status},
            timeout=timeout or self.config.timeout_default,
        )
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
        response = self._request(
            "POST",
            f"{self.experiment_server_url}experiment/{experiment_id}/continue",
            timeout=timeout or self.config.timeout_default,
        )
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
        response = self._request(
            "POST",
            f"{self.experiment_server_url}experiment/{experiment_id}/pause",
            timeout=timeout or self.config.timeout_default,
        )
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
        response = self._request(
            "POST",
            f"{self.experiment_server_url}experiment/{experiment_id}/cancel",
            timeout=timeout or self.config.timeout_default,
        )
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
        response = self._request(
            "POST",
            f"{self.experiment_server_url}campaign",
            json=campaign.model_dump(mode="json"),
            timeout=timeout or self.config.timeout_default,
        )
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
        response = self._request(
            "GET",
            f"{self.experiment_server_url}campaign/{campaign_id}",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Async methods
    # ------------------------------------------------------------------

    async def async_get_experiment(
        self, experiment_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> dict:
        """
        Get an experiment by ID asynchronously.

        Args:
            experiment_id: The ID of the experiment to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "GET",
            f"{self.experiment_server_url}experiment/{experiment_id}",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Experiment.model_validate(response.json())

    async def async_get_experiments(
        self, number: int = 10, timeout: Optional[float] = None
    ) -> list[Experiment]:
        """
        Get a list of the latest experiments asynchronously.

        Args:
            number: Number of experiments to retrieve.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "GET",
            f"{self.experiment_server_url}experiments",
            params={"number": number},
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [Experiment.model_validate(experiment) for experiment in response.json()]

    async def async_start_experiment(
        self,
        experiment_design: ExperimentDesign,
        run_name: Optional[str] = None,
        run_description: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> Experiment:
        """
        Start an experiment based on an ExperimentDesign asynchronously.

        Args:
            experiment_design: The design of the experiment to start.
            run_name: Optional name for the experiment run.
            run_description: Optional description for the experiment run.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "POST",
            f"{self.experiment_server_url}experiment",
            json=ExperimentRegistration(
                experiment_design=experiment_design.model_dump(mode="json"),
                run_name=run_name,
                run_description=run_description,
            ).model_dump(mode="json"),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Experiment.model_validate(response.json())

    async def async_end_experiment(
        self,
        experiment_id: Union[str, ULID],
        status: Optional[ExperimentStatus] = None,
        timeout: Optional[float] = None,
    ) -> Experiment:
        """
        End an experiment by ID asynchronously.

        Args:
            experiment_id: The ID of the experiment to end.
            status: Optional status to set on the experiment.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "POST",
            f"{self.experiment_server_url}experiment/{experiment_id}/end",
            params={"status": status},
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Experiment.model_validate(response.json())

    async def async_continue_experiment(
        self, experiment_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> Experiment:
        """
        Continue an experiment by ID asynchronously.

        Args:
            experiment_id: The ID of the experiment to continue.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "POST",
            f"{self.experiment_server_url}experiment/{experiment_id}/continue",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Experiment.model_validate(response.json())

    async def async_pause_experiment(
        self, experiment_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> Experiment:
        """
        Pause an experiment by ID asynchronously.

        Args:
            experiment_id: The ID of the experiment to pause.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "POST",
            f"{self.experiment_server_url}experiment/{experiment_id}/pause",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Experiment.model_validate(response.json())

    async def async_cancel_experiment(
        self, experiment_id: Union[str, ULID], timeout: Optional[float] = None
    ) -> Experiment:
        """
        Cancel an experiment by ID asynchronously.

        Args:
            experiment_id: The ID of the experiment to cancel.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "POST",
            f"{self.experiment_server_url}experiment/{experiment_id}/cancel",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Experiment.model_validate(response.json())

    async def async_register_campaign(
        self, campaign: ExperimentalCampaign, timeout: Optional[float] = None
    ) -> ExperimentalCampaign:
        """
        Register a new experimental campaign asynchronously.

        Args:
            campaign: The campaign to register.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "POST",
            f"{self.experiment_server_url}campaign",
            json=campaign.model_dump(mode="json"),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    async def async_get_campaign(
        self, campaign_id: str, timeout: Optional[float] = None
    ) -> ExperimentalCampaign:
        """
        Get an experimental campaign by ID asynchronously.

        Args:
            campaign_id: The ID of the campaign to get.
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "GET",
            f"{self.experiment_server_url}campaign/{campaign_id}",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()
