"""Client for performing location management actions."""

import time
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Union

import httpx
import yaml
from madsci.client.event_client import EventClient
from madsci.client.http import DualModeClientMixin
from madsci.common.context import get_current_madsci_context, get_event_client
from madsci.common.http_client import create_httpx_client
from madsci.common.ownership import get_current_ownership_info
from madsci.common.types.client_types import LocationClientConfig
from madsci.common.types.event_types import EventType
from madsci.common.types.location_types import (
    CreateLocationFromTemplateRequest,
    Location,
    LocationImportResult,
    LocationRepresentationTemplate,
    LocationTemplate,
)
from madsci.common.types.resource_types.server_types import ResourceHierarchy
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.common.warnings import MadsciLocalOnlyWarning
from pydantic import AnyUrl

_T = TypeVar("_T")


class LocationClient(DualModeClientMixin):
    """A client for interacting with the Location Manager to perform location operations."""

    location_server_url: Optional[AnyUrl]

    def __init__(
        self,
        location_server_url: Optional[Union[str, AnyUrl]] = None,
        event_client: Optional[EventClient] = None,
        config: Optional[LocationClientConfig] = None,
    ) -> None:
        """
        Initialize the LocationClient.

        Parameters
        ----------
        location_server_url : Optional[Union[str, AnyUrl]]
            The URL of the location server. If None, will try to get from context.
        event_client : Optional[EventClient]
            Event client for logging. If not provided, a new one will be created.
        config : Optional[LocationClientConfig]
            Client configuration for retry and timeout settings. If not provided, uses default LocationClientConfig.
        """
        # Set up location server URL
        if location_server_url is not None:
            if isinstance(location_server_url, str):
                self.location_server_url = AnyUrl(location_server_url)
            else:
                self.location_server_url = location_server_url
        else:
            context = get_current_madsci_context()
            self.location_server_url = context.location_server_url

        # Initialize logger - use injected client, context client, or create new
        if event_client is not None:
            self.logger = event_client
        else:
            self.logger = get_event_client(
                component_type="LocationClient",
                location_server=str(self.location_server_url)
                if self.location_server_url
                else None,
            )

        # Log warning if no URL is available
        if self.location_server_url is None:
            self.logger.warning(
                "LocationClient initialized without a URL. Location operations will fail unless a location server URL is configured in the MADSci context.",
                event_type=EventType.LOG_WARNING,
                warning_category=MadsciLocalOnlyWarning,
            )

        # Ensure URL ends with /
        if self.location_server_url and not str(self.location_server_url).endswith("/"):
            self.location_server_url = AnyUrl(str(self.location_server_url) + "/")

        # Store config and create httpx client
        self.config = config if config is not None else LocationClientConfig()
        self._client = create_httpx_client(config=self.config)
        self._async_client = None

    @property
    def session(self) -> httpx.Client:
        """Backward-compatible accessor for the underlying HTTP client."""
        return self._client

    def close(self) -> None:
        """Close HTTP clients and embedded logger."""
        super().close()
        if hasattr(self, "logger") and self.logger is not None:
            self.logger.close()

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

    def _call_with_startup_retry(self, fn: Callable[[], _T], operation_name: str) -> _T:
        """Call *fn* with exponential-backoff retries for connection errors.

        Used by the idempotent ``init_*`` template methods that run during node
        startup, when the location manager may not be ready yet.
        """
        max_attempts = self.config.startup_retry_max_attempts
        delay = self.config.startup_retry_initial_delay
        max_delay = self.config.startup_retry_max_delay
        backoff = self.config.startup_retry_backoff_factor

        for attempt in range(1, max_attempts + 1):
            try:
                return fn()
            except (httpx.ConnectError, ConnectionError) as exc:
                if attempt == max_attempts:
                    raise
                self.logger.warning(
                    "Connection failed, retrying",
                    event_type=EventType.LOG_WARNING,
                    operation=operation_name,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    retry_delay=round(delay, 1),
                    error=str(exc),
                )
                time.sleep(delay)
                delay = min(delay * backoff, max_delay)
        # Should not reach here, but satisfy type checker
        raise RuntimeError("Unreachable")  # pragma: no cover

    def _get_headers(self) -> dict[str, str]:
        """Get headers for requests including ownership information."""
        headers = {"Content-Type": "application/json"}

        ownership_info = get_current_ownership_info()
        if ownership_info and ownership_info.user_id:
            headers["X-Owner"] = ownership_info.user_id

        return headers

    # ------------------------------------------------------------------
    # Sync methods
    # ------------------------------------------------------------------

    def get_locations(self, timeout: Optional[float] = None) -> list[Location]:
        """
        Get all locations.

        Parameters
        ----------
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        list[Location]
            A list of all locations.
        """
        self._validate_server_url()

        response = self._request(
            "GET",
            f"{self.location_server_url}locations",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [Location.model_validate(loc) for loc in response.json()]

    def get_location(
        self, location_id: str, timeout: Optional[float] = None
    ) -> Location:
        """
        Get details of a specific location by ID.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        Location
            The location details.
        """
        self._validate_server_url()

        response = self._request(
            "GET",
            f"{self.location_server_url}location",
            params={"location_id": location_id},
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def get_location_by_name(
        self, location_name: str, timeout: Optional[float] = None
    ) -> Location:
        """
        Get a specific location by name.

        Parameters
        ----------
        location_name : str
            The name of the location to retrieve.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        Location
            The requested location.
        """
        self._validate_server_url()

        response = self._request(
            "GET",
            f"{self.location_server_url}location",
            params={"name": location_name},
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def add_location(
        self, location: Location, timeout: Optional[float] = None
    ) -> Location:
        """
        Add a location.

        Parameters
        ----------
        location : Location
            The location object to add.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        Location
            The created location.
        """
        self._validate_server_url()

        response = self._request(
            "POST",
            f"{self.location_server_url}location",
            json=location.model_dump(),
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def import_locations(
        self,
        location_file_path: Optional[Path] = None,
        locations: Optional[list[Location]] = None,
        overwrite: bool = False,
        timeout: Optional[float] = None,
    ) -> LocationImportResult:
        """
        Import multiple locations from a file or a list.

        Posts the full list to the server's /locations/import endpoint.

        Parameters
        ----------
        location_file_path : Optional[Path]
            Path to a YAML file containing location definitions.
        locations : Optional[list[Location]]
            A list of Location objects to import directly.
        overwrite : bool
            If True, overwrite existing locations with the same name.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        LocationImportResult
            Result with imported/skipped/error counts and imported locations.
        """
        self._validate_server_url()

        if locations is None:
            if location_file_path is None:
                raise ValueError(
                    "Either location_file_path or locations must be provided"
                )
            with location_file_path.open() as f:
                raw = yaml.safe_load(f)
            if raw is None:
                return LocationImportResult()
            if isinstance(raw, list):
                location_items = raw
            elif isinstance(raw, dict):
                location_items = list(raw.values())
            else:
                raise ValueError(
                    f"Expected a list or dict of locations, got {type(raw)}"
                )
            locations = [Location.model_validate(item) for item in location_items]

        response = self._request(
            "POST",
            f"{self.location_server_url}locations/import",
            json=[loc.model_dump() for loc in locations],
            params={"overwrite": overwrite},
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LocationImportResult.model_validate(response.json())

    def export_locations(self, timeout: Optional[float] = None) -> list[Location]:
        """
        Export all locations from the server.

        Parameters
        ----------
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        list[Location]
            All locations managed by the location server.
        """
        self._validate_server_url()

        response = self._request(
            "GET",
            f"{self.location_server_url}locations/export",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [Location.model_validate(loc) for loc in response.json()]

    # --- Representation Template Methods ---

    def get_representation_templates(
        self, timeout: Optional[float] = None
    ) -> list[LocationRepresentationTemplate]:
        """Get all representation templates."""
        self._validate_server_url()
        response = self._request(
            "GET",
            f"{self.location_server_url}representation_templates",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [
            LocationRepresentationTemplate.model_validate(t) for t in response.json()
        ]

    def get_representation_template(
        self, template_name: str, timeout: Optional[float] = None
    ) -> LocationRepresentationTemplate:
        """Get a representation template by name."""
        self._validate_server_url()
        response = self._request(
            "GET",
            f"{self.location_server_url}representation_template/{template_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LocationRepresentationTemplate.model_validate(response.json())

    def create_representation_template(
        self,
        template: LocationRepresentationTemplate,
        timeout: Optional[float] = None,
    ) -> LocationRepresentationTemplate:
        """Create a new representation template."""
        self._validate_server_url()
        response = self._request(
            "POST",
            f"{self.location_server_url}representation_template",
            json=template.model_dump(mode="json"),
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LocationRepresentationTemplate.model_validate(response.json())

    def init_representation_template(
        self,
        template_name: str,
        default_values: Optional[dict[str, Any]] = None,
        schema: Optional[dict[str, Any]] = None,
        required_overrides: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        created_by: Optional[str] = None,
        version: str = "1.0.0",
        description: Optional[str] = None,
        timeout: Optional[float] = None,
        schema_def: Optional[dict[str, Any]] = None,
    ) -> LocationRepresentationTemplate:
        """Idempotent init: get-or-create, version-update for a representation template.

        Retries with exponential backoff on connection errors to tolerate
        transient unavailability of the location manager during startup.

        The ``schema`` parameter is deprecated; use ``schema_def`` instead.
        If both are provided, ``schema_def`` takes precedence.
        """
        self._validate_server_url()
        resolved_schema = schema_def if schema_def is not None else schema
        template = LocationRepresentationTemplate(
            template_name=template_name,
            default_values=default_values or {},
            schema_def=resolved_schema,
            required_overrides=required_overrides or [],
            tags=tags or [],
            created_by=created_by,
            version=version,
            description=description,
        )

        def _do_init() -> LocationRepresentationTemplate:
            response = self._request(
                "POST",
                f"{self.location_server_url}representation_template/init",
                json=template.model_dump(mode="json"),
                headers=self._get_headers(),
                timeout=timeout or self.config.timeout_default,
            )
            response.raise_for_status()
            return LocationRepresentationTemplate.model_validate(response.json())

        return self._call_with_startup_retry(
            _do_init, f"init_representation_template({template_name!r})"
        )

    def delete_representation_template(
        self, template_name: str, timeout: Optional[float] = None
    ) -> dict[str, str]:
        """Delete a representation template by name."""
        self._validate_server_url()
        response = self._request(
            "DELETE",
            f"{self.location_server_url}representation_template/{template_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    # --- Location Template Methods ---

    def get_location_templates(
        self, timeout: Optional[float] = None
    ) -> list[LocationTemplate]:
        """Get all location templates."""
        self._validate_server_url()
        response = self._request(
            "GET",
            f"{self.location_server_url}location_templates",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [LocationTemplate.model_validate(t) for t in response.json()]

    def get_location_template(
        self, template_name: str, timeout: Optional[float] = None
    ) -> LocationTemplate:
        """Get a location template by name."""
        self._validate_server_url()
        response = self._request(
            "GET",
            f"{self.location_server_url}location_template/{template_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LocationTemplate.model_validate(response.json())

    def create_location_template(
        self,
        template: LocationTemplate,
        timeout: Optional[float] = None,
    ) -> LocationTemplate:
        """Create a new location template."""
        self._validate_server_url()
        response = self._request(
            "POST",
            f"{self.location_server_url}location_template",
            json=template.model_dump(mode="json"),
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LocationTemplate.model_validate(response.json())

    def init_location_template(
        self,
        template_name: str,
        representation_templates: Optional[dict[str, str]] = None,
        resource_template_name: Optional[str] = None,
        resource_template_overrides: Optional[dict[str, Any]] = None,
        default_allow_transfers: bool = True,
        tags: Optional[list[str]] = None,
        created_by: Optional[str] = None,
        version: str = "1.0.0",
        description: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> LocationTemplate:
        """Idempotent init: get-or-create, version-update for a location template.

        Retries with exponential backoff on connection errors to tolerate
        transient unavailability of the location manager during startup.
        """
        self._validate_server_url()
        template = LocationTemplate(
            template_name=template_name,
            representation_templates=representation_templates or {},
            resource_template_name=resource_template_name,
            resource_template_overrides=resource_template_overrides,
            default_allow_transfers=default_allow_transfers,
            tags=tags or [],
            created_by=created_by,
            version=version,
            description=description,
        )

        def _do_init() -> LocationTemplate:
            response = self._request(
                "POST",
                f"{self.location_server_url}location_template/init",
                json=template.model_dump(mode="json"),
                headers=self._get_headers(),
                timeout=timeout or self.config.timeout_default,
            )
            response.raise_for_status()
            return LocationTemplate.model_validate(response.json())

        return self._call_with_startup_retry(
            _do_init, f"init_location_template({template_name!r})"
        )

    def delete_location_template(
        self, template_name: str, timeout: Optional[float] = None
    ) -> dict[str, str]:
        """Delete a location template by name."""
        self._validate_server_url()
        response = self._request(
            "DELETE",
            f"{self.location_server_url}location_template/{template_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    # --- Create Location from Template ---

    def create_location_from_template(
        self,
        location_name: str,
        template_name: str,
        node_bindings: Optional[dict[str, str]] = None,
        representation_overrides: Optional[dict[str, dict[str, Any]]] = None,
        resource_template_overrides: Optional[dict[str, Any]] = None,
        description: Optional[str] = None,
        allow_transfers: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> Location:
        """Create a location from a LocationTemplate."""
        self._validate_server_url()
        request = CreateLocationFromTemplateRequest(
            location_name=location_name,
            template_name=template_name,
            node_bindings=node_bindings or {},
            representation_overrides=representation_overrides or {},
            resource_template_overrides=resource_template_overrides,
            description=description,
            allow_transfers=allow_transfers,
        )
        response = self._request(
            "POST",
            f"{self.location_server_url}location/from_template",
            json=request.model_dump(mode="json"),
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def delete_location(
        self, location_name: str, timeout: Optional[float] = None
    ) -> dict[str, str]:
        """
        Delete a specific location by name.

        Parameters
        ----------
        location_name : str
            The name of the location to delete.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        dict[str, str]
            A message confirming deletion.
        """
        self._validate_server_url()

        response = self._request(
            "DELETE",
            f"{self.location_server_url}location/{location_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    def set_representation(
        self,
        location_name: str,
        node_name: str,
        representation: Any,
        timeout: Optional[float] = None,
    ) -> Location:
        """
        Set a representation for a location for a specific node.

        Parameters
        ----------
        location_name : str
            The name of the location.
        node_name : str
            The name of the node.
        representation : Any
            The representation to set for the specified node.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        Location
            The updated location.
        """
        self._validate_server_url()

        response = self._request(
            "POST",
            f"{self.location_server_url}location/{location_name}/set_representation/{node_name}",
            json=representation,
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def remove_representation(
        self,
        location_name: str,
        node_name: str,
        timeout: Optional[float] = None,
    ) -> Location:
        """
        Remove representations for a location for a specific node.

        Parameters
        ----------
        location_name : str
            The name of the location.
        node_name : str
            The name of the node.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        Location
            The updated location.
        """
        self._validate_server_url()

        response = self._request(
            "DELETE",
            f"{self.location_server_url}location/{location_name}/remove_representation/{node_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def attach_resource(
        self, location_name: str, resource_id: str, timeout: Optional[float] = None
    ) -> Location:
        """
        Attach a resource to a location.

        Parameters
        ----------
        location_name : str
            The name of the location.
        resource_id : str
            The ID of the resource to attach.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        Location
            The updated location.
        """
        self._validate_server_url()

        response = self._request(
            "POST",
            f"{self.location_server_url}location/{location_name}/attach_resource",
            params={"resource_id": resource_id},
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def detach_resource(
        self, location_name: str, timeout: Optional[float] = None
    ) -> Location:
        """
        Detach the resource from a location.

        Parameters
        ----------
        location_name : str
            The name of the location.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        Location
            The updated location.
        """
        self._validate_server_url()

        response = self._request(
            "DELETE",
            f"{self.location_server_url}location/{location_name}/detach_resource",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    def get_transfer_graph(
        self, timeout: Optional[float] = None
    ) -> dict[str, list[str]]:
        """
        Get the current transfer graph as adjacency list.

        Parameters
        ----------
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        dict[str, list[str]]
            Transfer graph as adjacency list mapping source location IDs to
            lists of reachable destination location IDs.
        """
        self._validate_server_url()

        response = self._request(
            "GET",
            f"{self.location_server_url}transfer/graph",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    def plan_transfer(
        self,
        source_location_id: str,
        target_location_id: str,
        resource_id: Optional[str] = None,
        timeout: Optional[float] = None,
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
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        WorkflowDefinition
            A WorkflowDefinition including the necessary steps to transfer a resource between locations.
        """
        self._validate_server_url()

        params = {
            "source_location_id": source_location_id,
            "target_location_id": target_location_id,
        }
        if resource_id is not None:
            params["resource_id"] = resource_id

        response = self._request(
            "POST",
            f"{self.location_server_url}transfer/plan",
            params=params,
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return WorkflowDefinition.model_validate(response.json())

    def get_location_resources(
        self, location_name: str, timeout: Optional[float] = None
    ) -> ResourceHierarchy:
        """
        Get the resource hierarchy for resources currently at a specific location.

        Parameters
        ----------
        location_name : str
            The name of the location.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        ResourceHierarchy
            Hierarchy of resources at the location, or empty hierarchy if no attached resource.
        """
        self._validate_server_url()

        response = self._request(
            "GET",
            f"{self.location_server_url}location/{location_name}/resources",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return ResourceHierarchy.model_validate(response.json())

    # ------------------------------------------------------------------
    # Async methods
    # ------------------------------------------------------------------

    async def async_get_locations(
        self, timeout: Optional[float] = None
    ) -> list[Location]:
        """Get all locations asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "GET",
            f"{self.location_server_url}locations",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [Location.model_validate(loc) for loc in response.json()]

    async def async_get_location(
        self, location_id: str, timeout: Optional[float] = None
    ) -> Location:
        """Get details of a specific location by ID asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "GET",
            f"{self.location_server_url}location",
            params={"location_id": location_id},
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    async def async_get_location_by_name(
        self, location_name: str, timeout: Optional[float] = None
    ) -> Location:
        """Get a specific location by name asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "GET",
            f"{self.location_server_url}location",
            params={"name": location_name},
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    async def async_add_location(
        self, location: Location, timeout: Optional[float] = None
    ) -> Location:
        """Add a location asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "POST",
            f"{self.location_server_url}location",
            json=location.model_dump(),
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    async def async_export_locations(
        self, timeout: Optional[float] = None
    ) -> list[Location]:
        """Export all locations from the server asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "GET",
            f"{self.location_server_url}locations/export",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [Location.model_validate(loc) for loc in response.json()]

    async def async_delete_location(
        self, location_name: str, timeout: Optional[float] = None
    ) -> dict[str, str]:
        """Delete a specific location by name asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "DELETE",
            f"{self.location_server_url}location/{location_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    async def async_set_representation(
        self,
        location_name: str,
        node_name: str,
        representation: Any,
        timeout: Optional[float] = None,
    ) -> Location:
        """Set a representation for a location for a specific node asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "POST",
            f"{self.location_server_url}location/{location_name}/set_representation/{node_name}",
            json=representation,
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    async def async_remove_representation(
        self,
        location_name: str,
        node_name: str,
        timeout: Optional[float] = None,
    ) -> Location:
        """Remove representations for a location for a specific node asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "DELETE",
            f"{self.location_server_url}location/{location_name}/remove_representation/{node_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    async def async_attach_resource(
        self, location_name: str, resource_id: str, timeout: Optional[float] = None
    ) -> Location:
        """Attach a resource to a location asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "POST",
            f"{self.location_server_url}location/{location_name}/attach_resource",
            params={"resource_id": resource_id},
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    async def async_detach_resource(
        self, location_name: str, timeout: Optional[float] = None
    ) -> Location:
        """Detach the resource from a location asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "DELETE",
            f"{self.location_server_url}location/{location_name}/detach_resource",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    async def async_get_transfer_graph(
        self, timeout: Optional[float] = None
    ) -> dict[str, list[str]]:
        """Get the current transfer graph as adjacency list asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "GET",
            f"{self.location_server_url}transfer/graph",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    async def async_plan_transfer(
        self,
        source_location_id: str,
        target_location_id: str,
        resource_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """Plan a transfer from source to target location asynchronously."""
        self._validate_server_url()
        params = {
            "source_location_id": source_location_id,
            "target_location_id": target_location_id,
        }
        if resource_id is not None:
            params["resource_id"] = resource_id
        response = await self._async_request(
            "POST",
            f"{self.location_server_url}transfer/plan",
            params=params,
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return WorkflowDefinition.model_validate(response.json())

    async def async_get_location_resources(
        self, location_name: str, timeout: Optional[float] = None
    ) -> ResourceHierarchy:
        """Get the resource hierarchy for resources at a specific location asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "GET",
            f"{self.location_server_url}location/{location_name}/resources",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return ResourceHierarchy.model_validate(response.json())

    # --- Async Representation Template Methods ---

    async def async_get_representation_templates(
        self, timeout: Optional[float] = None
    ) -> list[LocationRepresentationTemplate]:
        """Get all representation templates asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "GET",
            f"{self.location_server_url}representation_templates",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [
            LocationRepresentationTemplate.model_validate(t) for t in response.json()
        ]

    async def async_get_representation_template(
        self, template_name: str, timeout: Optional[float] = None
    ) -> LocationRepresentationTemplate:
        """Get a representation template by name asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "GET",
            f"{self.location_server_url}representation_template/{template_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LocationRepresentationTemplate.model_validate(response.json())

    async def async_create_representation_template(
        self,
        template: LocationRepresentationTemplate,
        timeout: Optional[float] = None,
    ) -> LocationRepresentationTemplate:
        """Create a new representation template asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "POST",
            f"{self.location_server_url}representation_template",
            json=template.model_dump(mode="json"),
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LocationRepresentationTemplate.model_validate(response.json())

    async def async_delete_representation_template(
        self, template_name: str, timeout: Optional[float] = None
    ) -> dict[str, str]:
        """Delete a representation template by name asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "DELETE",
            f"{self.location_server_url}representation_template/{template_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    # --- Async Location Template Methods ---

    async def async_get_location_templates(
        self, timeout: Optional[float] = None
    ) -> list[LocationTemplate]:
        """Get all location templates asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "GET",
            f"{self.location_server_url}location_templates",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return [LocationTemplate.model_validate(t) for t in response.json()]

    async def async_get_location_template(
        self, template_name: str, timeout: Optional[float] = None
    ) -> LocationTemplate:
        """Get a location template by name asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "GET",
            f"{self.location_server_url}location_template/{template_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LocationTemplate.model_validate(response.json())

    async def async_create_location_template(
        self,
        template: LocationTemplate,
        timeout: Optional[float] = None,
    ) -> LocationTemplate:
        """Create a new location template asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "POST",
            f"{self.location_server_url}location_template",
            json=template.model_dump(mode="json"),
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LocationTemplate.model_validate(response.json())

    async def async_delete_location_template(
        self, template_name: str, timeout: Optional[float] = None
    ) -> dict[str, str]:
        """Delete a location template by name asynchronously."""
        self._validate_server_url()
        response = await self._async_request(
            "DELETE",
            f"{self.location_server_url}location_template/{template_name}",
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return response.json()

    # --- Async Create Location from Template ---

    async def async_create_location_from_template(
        self,
        location_name: str,
        template_name: str,
        node_bindings: Optional[dict[str, str]] = None,
        representation_overrides: Optional[dict[str, dict[str, Any]]] = None,
        resource_template_overrides: Optional[dict[str, Any]] = None,
        description: Optional[str] = None,
        allow_transfers: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> Location:
        """Create a location from a LocationTemplate asynchronously."""
        self._validate_server_url()
        request = CreateLocationFromTemplateRequest(
            location_name=location_name,
            template_name=template_name,
            node_bindings=node_bindings or {},
            representation_overrides=representation_overrides or {},
            resource_template_overrides=resource_template_overrides,
            description=description,
            allow_transfers=allow_transfers,
        )
        response = await self._async_request(
            "POST",
            f"{self.location_server_url}location/from_template",
            json=request.model_dump(mode="json"),
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return Location.model_validate(response.json())

    # --- Async Import ---

    async def async_import_locations(
        self,
        location_file_path: Optional[Path] = None,
        locations: Optional[list[Location]] = None,
        overwrite: bool = False,
        timeout: Optional[float] = None,
    ) -> LocationImportResult:
        """Import multiple locations from a file or a list asynchronously.

        Parameters
        ----------
        location_file_path : Optional[Path]
            Path to a YAML file containing location definitions.
        locations : Optional[list[Location]]
            A list of Location objects to import directly.
        overwrite : bool
            If True, overwrite existing locations with the same name.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        LocationImportResult
            Result with imported/skipped/error counts and imported locations.
        """
        self._validate_server_url()

        if locations is None:
            if location_file_path is None:
                raise ValueError(
                    "Either location_file_path or locations must be provided"
                )
            with location_file_path.open() as f:
                raw = yaml.safe_load(f)
            if raw is None:
                return LocationImportResult()
            if isinstance(raw, list):
                location_items = raw
            elif isinstance(raw, dict):
                location_items = list(raw.values())
            else:
                raise ValueError(
                    f"Expected a list or dict of locations, got {type(raw)}"
                )
            locations = [Location.model_validate(item) for item in location_items]

        response = await self._async_request(
            "POST",
            f"{self.location_server_url}locations/import",
            json=[loc.model_dump() for loc in locations],
            params={"overwrite": overwrite},
            headers=self._get_headers(),
            timeout=timeout or self.config.timeout_default,
        )
        response.raise_for_status()
        return LocationImportResult.model_validate(response.json())
