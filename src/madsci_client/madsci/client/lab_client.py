"""Client for the MADSci Lab Manager."""

from typing import Optional, Union

from madsci.common.context import get_current_madsci_context
from madsci.common.types.client_types import LabClientConfig
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.lab_types import LabHealth, LabManagerDefinition
from madsci.common.types.manager_types import ManagerHealth
from madsci.common.utils import create_http_session
from pydantic import AnyUrl


class LabClient:
    """Client for the MADSci Lab Manager."""

    lab_server_url: AnyUrl

    def __init__(
        self,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
        config: Optional[LabClientConfig] = None,
    ) -> "LabClient":
        """
        Create a new Lab Client.

        Args:
            lab_server_url: The URL of the lab server. If not provided, will use the URL from the current MADSci context.
            config: Client configuration for retry and timeout settings. If not provided, uses default LabClientConfig.
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

        # Store config and create session
        self.config = config if config is not None else LabClientConfig()
        self.session = create_http_session(config=self.config)

    def get_lab_context(self, timeout: Optional[float] = None) -> MadsciContext:
        """
        Get the lab context.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.lab_server_url}context",
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return MadsciContext.model_validate(response.json())

    def get_manager_health(self, timeout: Optional[float] = None) -> ManagerHealth:
        """
        Get the health of the lab manager.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.lab_server_url}health",
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return ManagerHealth.model_validate(response.json())

    def get_lab_health(self, timeout: Optional[float] = None) -> LabHealth:
        """
        Get the health of the lab.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.lab_server_url}lab_health",
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return LabHealth.model_validate(response.json())

    def get_definition(self, timeout: Optional[float] = None) -> LabManagerDefinition:
        """
        Get the definition of the lab.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self.session.get(
            f"{self.lab_server_url}definition",
            timeout=timeout or self.config.timeout_default,
        )
        if not response.ok:
            response.raise_for_status()
        return LabManagerDefinition.model_validate(response.json())
