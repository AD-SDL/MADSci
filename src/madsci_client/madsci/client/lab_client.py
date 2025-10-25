"""Client for the MADSci Experiment Manager."""

from typing import Optional, Union

import requests
from madsci.common.context import get_current_madsci_context
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.lab_types import LabHealth, LabManagerDefinition
from madsci.common.types.manager_types import ManagerHealth
from pydantic import AnyUrl


class LabClient:
    """Client for the MADSci Lab Manager."""

    lab_server_url: AnyUrl

    def __init__(
        self,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
    ) -> "LabClient":
        """
        Create a new Lab Client.

        Args:
            experiment_server_url: The URL of the experiment server. If not provided, will use the URL from the current MADSci context.
        """
        self.lab_server_url = (
            AnyUrl(lab_server_url)
            if lab_server_url
            else get_current_madsci_context().lab_server_url
        )
        if not self.lab_server_url:
            raise ValueError(
                "No lab server URL provided, please specify a URL or set the context."
            )

    def get_lab_context(self) -> MadsciContext:
        """Get an experiment by ID."""
        response = requests.get(f"{self.lab_server_url}context", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return MadsciContext.model_validate(response.json())

    def get_manager_health(self) -> ManagerHealth:
        """Get the health of the lab."""
        response = requests.get(f"{self.lab_server_url}health", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return ManagerHealth.model_validate(response.json())

    def get_lab_health(self) -> LabHealth:
        """Get the health of the lab."""
        response = requests.get(f"{self.lab_server_url}lab_health", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return LabHealth.model_validate(response.json())

    def get_definition(self) -> LabManagerDefinition:
        """Get the definition of the lab."""
        response = requests.get(f"{self.lab_server_url}definition", timeout=10)
        if not response.ok:
            response.raise_for_status()
        return LabManagerDefinition.model_validate(response.json())
