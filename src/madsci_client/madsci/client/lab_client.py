"""Client for the MADSci Lab Manager."""

from __future__ import annotations

from typing import Optional, Union

import httpx
from madsci.client.http import DualModeClientMixin
from madsci.common.context import get_current_madsci_context
from madsci.common.http_client import create_httpx_client
from madsci.common.types.client_types import LabClientConfig
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.lab_types import LabHealth
from madsci.common.types.manager_types import ManagerHealth
from pydantic import AnyUrl


class LabClient(DualModeClientMixin):
    """Client for the MADSci Lab Manager."""

    lab_server_url: AnyUrl

    def __init__(
        self,
        lab_server_url: Optional[Union[str, AnyUrl]] = None,
        config: Optional[LabClientConfig] = None,
    ) -> None:
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

        # Store config and create httpx client
        self.config = config if config is not None else LabClientConfig()
        self._client = create_httpx_client(config=self.config)
        self._async_client = None

    @property
    def session(self) -> httpx.Client:
        """Backward-compatible accessor for the underlying HTTP client.

        Returns the httpx.Client so that existing code accessing
        ``client.session`` continues to work.
        """
        return self._client

    # ------------------------------------------------------------------
    # Sync methods
    # ------------------------------------------------------------------

    def get_lab_context(self, timeout: Optional[float] = None) -> MadsciContext:
        """
        Get the lab context.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self._request(
            "GET",
            f"{self.lab_server_url}context",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return MadsciContext.model_validate(response.json())

    def get_manager_health(self, timeout: Optional[float] = None) -> ManagerHealth:
        """
        Get the health of the lab manager.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self._request(
            "GET",
            f"{self.lab_server_url}health",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return ManagerHealth.model_validate(response.json())

    def get_lab_health(self, timeout: Optional[float] = None) -> LabHealth:
        """
        Get the health of the lab.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = self._request(
            "GET",
            f"{self.lab_server_url}lab_health",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LabHealth.model_validate(response.json())

    # ------------------------------------------------------------------
    # Async methods
    # ------------------------------------------------------------------

    async def async_get_lab_context(
        self, timeout: Optional[float] = None
    ) -> MadsciContext:
        """
        Get the lab context asynchronously.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "GET",
            f"{self.lab_server_url}context",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return MadsciContext.model_validate(response.json())

    async def async_get_manager_health(
        self, timeout: Optional[float] = None
    ) -> ManagerHealth:
        """
        Get the health of the lab manager asynchronously.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "GET",
            f"{self.lab_server_url}health",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return ManagerHealth.model_validate(response.json())

    async def async_get_lab_health(self, timeout: Optional[float] = None) -> LabHealth:
        """
        Get the health of the lab asynchronously.

        Args:
            timeout: Optional timeout override in seconds. If None, uses config.timeout_default.
        """
        response = await self._async_request(
            "GET",
            f"{self.lab_server_url}lab_health",
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LabHealth.model_validate(response.json())
