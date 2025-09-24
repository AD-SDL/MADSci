"""Client for performing location management actions."""

from typing import Any, Optional, Union

import requests
from madsci.client.event_client import EventClient
from madsci.common.context import get_current_madsci_context
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.location_types import Location
from madsci.common.types.resource_types.server_types import ResourceHierarchy
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.common.warnings import MadsciLocalOnlyWarning
from pydantic import AnyUrl
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class LocationClient:
    """A client for interacting with the Location Manager to perform location operations."""

    location_server_url: Optional[AnyUrl]

    def __init__(
        self,
        location_server_url: Optional[Union[str, AnyUrl]] = None,
        event_client: Optional[EventClient] = None,
        retry: bool = False,
        retry_total: int = 3,
        retry_backoff_factor: float = 0.3,
        retry_status_forcelist: Optional[list[int]] = None,
    ) -> None:
        """
        Initialize the LocationClient.

        Parameters
        ----------
        location_server_url : Optional[Union[str, AnyUrl]]
            The URL of the location server. If None, will try to get from context.
        event_client : Optional[EventClient]
            Event client for logging. If not provided, a new one will be created.
        retry : bool
            Whether to enable request retries.
        retry_total : int
            Total number of retries.
        retry_backoff_factor : float
            Backoff factor for retries.
        retry_status_forcelist : Optional[list[int]]
            HTTP status codes to retry on.
        """
        self.retry = retry

        # Set up location server URL
        if location_server_url is not None:
            if isinstance(location_server_url, str):
                self.location_server_url = AnyUrl(location_server_url)
            else:
                self.location_server_url = location_server_url
        else:
            context = get_current_madsci_context()
            self.location_server_url = context.location_server_url

        # Initialize logger
        self.logger = event_client if event_client is not None else EventClient()

        # Log warning if no URL is available
        if self.location_server_url is None:
            self.logger.warning(
                "LocationClient initialized without a URL. Location operations will fail unless a location server URL is configured in the MADSci context.",
                warning_category=MadsciLocalOnlyWarning,
            )

        # Ensure URL ends with /
        if self.location_server_url and not str(self.location_server_url).endswith("/"):
            self.location_server_url = AnyUrl(str(self.location_server_url) + "/")

        # Set up retry strategy
        if retry_status_forcelist is None:
            retry_status_forcelist = [500, 502, 503, 504]

        retry_strategy = Retry(
            total=retry_total,
            status_forcelist=retry_status_forcelist,
            backoff_factor=retry_backoff_factor,
        )

        # Create sessions with and without retry
        self.session = requests.Session()
        self.session_no_retry = requests.Session()

        if self.retry:
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)

    def _validate_server_url(self) -> None:
        """
        Validate that location server URL is configured.

        Raises:
            ValueError: If location server URL is None.
        """
        if self.location_server_url is None:
            raise ValueError(
                "Location server URL not configured. Cannot perform location operations without a server URL."
            )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for requests including ownership information."""
        headers = {"Content-Type": "application/json"}

        ownership_info = get_current_ownership_info()
        if ownership_info and ownership_info.user_id:
            headers["X-Owner"] = ownership_info.user_id

        return headers

    def get_locations(self, retry: Optional[bool] = None) -> list[Location]:
        """
        Get all locations.

        Parameters
        ----------
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        list[Location]
            A list of all locations.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.get(
            f"{self.location_server_url}locations",
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return [Location.model_validate(loc) for loc in response.json()]

    def get_location(self, location_id: str, retry: Optional[bool] = None) -> Location:
        """
        Get details of a specific location.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        Location
            The location details.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.get(
            f"{self.location_server_url}location/{location_id}",
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def get_location_by_name(
        self, location_name: str, retry: Optional[bool] = None
    ) -> Location:
        """
        Get a specific location by name.

        Parameters
        ----------
        location_name : str
            The name of the location to retrieve.
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        Location
            The requested location.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.get(
            f"{self.location_server_url}location",
            params={"name": location_name},
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def add_location(
        self, location: Location, retry: Optional[bool] = None
    ) -> Location:
        """
        Add a location.

        Parameters
        ----------
        location : Location
            The location object to add.
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        Location
            The created location.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.post(
            f"{self.location_server_url}location",
            json=location.model_dump(),
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def delete_location(
        self, location_id: str, retry: Optional[bool] = None
    ) -> dict[str, str]:
        """
        Delete a specific location.

        Parameters
        ----------
        location_id : str
            The ID of the location to delete.
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        dict[str, str]
            A message confirming deletion.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.delete(
            f"{self.location_server_url}location/{location_id}",
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def set_representations(
        self,
        location_id: str,
        node_name: str,
        representation: Any,
        retry: Optional[bool] = None,
    ) -> Location:
        """
        Set a representation for a location for a specific node.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        node_name : str
            The name of the node.
        representation : Any
            The representation to set for the specified node.
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        Location
            The updated location.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.post(
            f"{self.location_server_url}location/{location_id}/set_representation/{node_name}",
            json=representation,
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def remove_representation(
        self,
        location_id: str,
        node_name: str,
        retry: Optional[bool] = None,
    ) -> Location:
        """
        Remove representations for a location for a specific node.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        node_name : str
            The name of the node.
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        Location
            The updated location.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.delete(
            f"{self.location_server_url}location/{location_id}/remove_representation/{node_name}",
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def attach_resource(
        self, location_id: str, resource_id: str, retry: Optional[bool] = None
    ) -> Location:
        """
        Attach a resource to a location.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        resource_id : str
            The ID of the resource to attach.
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        Location
            The updated location.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.post(
            f"{self.location_server_url}location/{location_id}/attach_resource",
            params={"resource_id": resource_id},
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def detach_resource(
        self, location_id: str, retry: Optional[bool] = None
    ) -> Location:
        """
        Detach the resource from a location.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        Location
            The updated location.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.delete(
            f"{self.location_server_url}location/{location_id}/detach_resource",
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def get_transfer_graph(self, retry: Optional[bool] = None) -> dict[str, list[str]]:
        """
        Get the current transfer graph as adjacency list.

        Parameters
        ----------
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        dict[str, list[str]]
            Transfer graph as adjacency list mapping source location IDs to
            lists of reachable destination location IDs.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.get(
            f"{self.location_server_url}transfer/graph",
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def plan_transfer(
        self,
        source_location_id: str,
        target_location_id: str,
        resource_id: Optional[str] = None,
        retry: Optional[bool] = None,
    ) -> dict[str, Any]:
        """
        Plan a transfer from source to target location.

        Parameters
        ----------
        source_location_id : str
            ID of the source location.
        target_location_id : str
            ID of the target location.
        resource_id : Optional[str]
            ID of the resource to transfer (for transfer_resource actions).
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        WorkflowDefinition
            A WorkflowDefinition including the necessary steps to transfer a resource between locations.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        params = {
            "source_location_id": source_location_id,
            "target_location_id": target_location_id,
        }
        if resource_id is not None:
            params["resource_id"] = resource_id

        response = session.post(
            f"{self.location_server_url}transfer/plan",
            params=params,
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return WorkflowDefinition.model_validate(response.json())

    def get_location_resources(
        self, location_id: str, retry: Optional[bool] = None
    ) -> ResourceHierarchy:
        """
        Get the resource hierarchy for resources currently at a specific location.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        retry : Optional[bool]
            Whether to use retry for this request. If None, uses instance default.

        Returns
        -------
        ResourceHierarchy
            Hierarchy of resources at the location, or empty hierarchy if no attached resource.
        """
        self._validate_server_url()
        if retry is None:
            retry = self.retry
        session = self.session if retry else self.session_no_retry

        response = session.get(
            f"{self.location_server_url}location/{location_id}/resources",
            headers=self._get_headers(),
            timeout=10,
        )
        response.raise_for_status()
        return ResourceHierarchy.model_validate(response.json())
