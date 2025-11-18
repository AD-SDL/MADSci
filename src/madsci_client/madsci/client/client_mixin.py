"""
Mixin class for managing MADSci client lifecycle.

This module provides a reusable mixin that handles client initialization,
configuration, and lifecycle management across MADSci components.
"""

from typing import Any, ClassVar, Optional, Union

from madsci.client.data_client import DataClient
from madsci.client.event_client import EventClient
from madsci.client.experiment_client import ExperimentClient
from madsci.client.lab_client import LabClient
from madsci.client.location_client import LocationClient
from madsci.client.resource_client import ResourceClient
from madsci.client.workcell_client import WorkcellClient
from madsci.common.types.datapoint_types import ObjectStorageSettings
from madsci.common.types.event_types import EventClientConfig
from pydantic import AnyUrl


class MadsciClientMixin:
    """
    Mixin for managing MADSci client lifecycle.

    Provides automatic initialization and management of MADSci service clients
    with support for:
    - Context-based auto-configuration
    - Explicit URL overrides
    - Selective client initialization
    - EventClient sharing across clients
    - Lazy initialization

    Usage:
        class MyComponent(MadsciClientMixin):
            # Optional: Declare which clients to initialize eagerly
            REQUIRED_CLIENTS = ["event", "resource", "data"]

            def __init__(self):
                super().__init__()
                self.setup_clients()  # Initialize required clients

            def my_method(self):
                # Access clients via properties
                self.event_client.info("Hello")
                self.resource_client.get_resource("xyz")

    Class Attributes:
        REQUIRED_CLIENTS: List of client names to initialize in setup_clients().
                         Available: "event", "resource", "data", "experiment",
                                   "workcell", "location", "lab"
        OPTIONAL_CLIENTS: List of client names that may be used but aren't required.

    Client Properties:
        event_client: EventClient for logging and event management
        resource_client: ResourceClient for resource and inventory tracking
        data_client: DataClient for data storage and retrieval
        experiment_client: ExperimentClient for experiment management
        workcell_client: WorkcellClient for workflow coordination
        location_client: LocationClient for location management
        lab_client: LabClient for lab configuration and context

    Configuration:
        The mixin supports several ways to configure clients:
        1. Context-based (default): URLs from get_current_madsci_context()
        2. Explicit URLs: Pass *_server_url as instance attributes
        3. Client configs: Pass *_client_config as instance attributes
        4. Direct injection: Pass pre-initialized clients to setup_clients()
    """

    # Class attributes for declaring client requirements
    REQUIRED_CLIENTS: ClassVar[list[str]] = []
    OPTIONAL_CLIENTS: ClassVar[list[str]] = []

    # Private attributes for client instances
    _event_client: Optional[EventClient] = None
    _resource_client: Optional[ResourceClient] = None
    _data_client: Optional[DataClient] = None
    _experiment_client: Optional[ExperimentClient] = None
    _workcell_client: Optional[WorkcellClient] = None
    _location_client: Optional[LocationClient] = None
    _lab_client: Optional[LabClient] = None

    # Configuration attributes (can be set by subclasses or instances)
    event_client_config: Optional[EventClientConfig] = None
    event_server_url: Optional[Union[str, AnyUrl]] = None
    resource_server_url: Optional[Union[str, AnyUrl]] = None
    data_server_url: Optional[Union[str, AnyUrl]] = None
    experiment_server_url: Optional[Union[str, AnyUrl]] = None
    workcell_server_url: Optional[Union[str, AnyUrl]] = None
    location_server_url: Optional[Union[str, AnyUrl]] = None
    lab_server_url: Optional[Union[str, AnyUrl]] = None

    # Client-specific configuration options
    object_storage_settings: Optional[ObjectStorageSettings] = None
    workcell_working_directory: str = "./"
    client_retry_enabled: bool = False
    client_retry_total: int = 3
    client_retry_backoff_factor: float = 0.3
    client_retry_status_forcelist: Optional[list[int]] = None

    def setup_clients(
        self,
        clients: Optional[list[str]] = None,
        event_client: Optional[EventClient] = None,
        resource_client: Optional[ResourceClient] = None,
        data_client: Optional[DataClient] = None,
        experiment_client: Optional[ExperimentClient] = None,
        workcell_client: Optional[WorkcellClient] = None,
        location_client: Optional[LocationClient] = None,
        lab_client: Optional[LabClient] = None,
    ) -> None:
        """
        Initialize specified clients.

        This method initializes the clients specified in the 'clients' parameter,
        or all REQUIRED_CLIENTS if not specified. Clients can also be directly
        injected as parameters (useful for testing).

        Args:
            clients: List of client names to initialize. If None, initializes
                    all clients in REQUIRED_CLIENTS. Available: "event",
                    "resource", "data", "experiment", "workcell", "location", "lab"
            event_client: Pre-initialized EventClient to use
            resource_client: Pre-initialized ResourceClient to use
            data_client: Pre-initialized DataClient to use
            experiment_client: Pre-initialized ExperimentClient to use
            workcell_client: Pre-initialized WorkcellClient to use
            location_client: Pre-initialized LocationClient to use
            lab_client: Pre-initialized LabClient to use

        Example:
            # Initialize required clients
            self.setup_clients()

            # Initialize specific clients
            self.setup_clients(clients=["event", "resource"])

            # Inject a mock client for testing
            mock_event = Mock(spec=EventClient)
            self.setup_clients(event_client=mock_event)
        """
        # Determine which clients to initialize
        clients_to_init = clients or self.REQUIRED_CLIENTS

        # Inject pre-initialized clients if provided
        injected_clients = {
            "event": event_client,
            "resource": resource_client,
            "data": data_client,
            "experiment": experiment_client,
            "workcell": workcell_client,
            "location": location_client,
            "lab": lab_client,
        }

        for name, client in injected_clients.items():
            if client is not None:
                setattr(self, f"_{name}_client", client)

        # Initialize clients in the specified order
        # EventClient first, then others (they may depend on EventClient)
        if "event" in clients_to_init and self._event_client is None:
            _ = self.event_client  # Trigger lazy initialization

        # Initialize remaining clients
        self._init_client_batch(clients_to_init)

    def _init_client_batch(self, clients_to_init: list[str]) -> None:
        """
        Helper method to initialize a batch of clients.

        Args:
            clients_to_init: List of client names to initialize
        """
        # Mapping of client names to their property accessors and private attributes
        client_map = {
            "resource": (self.resource_client, "_resource_client"),
            "data": (self.data_client, "_data_client"),
            "experiment": (self.experiment_client, "_experiment_client"),
            "workcell": (self.workcell_client, "_workcell_client"),
            "location": (self.location_client, "_location_client"),
            "lab": (self.lab_client, "_lab_client"),
        }

        for client_name in clients_to_init:
            if client_name == "event":
                continue  # Already handled in setup_clients
            if (
                client_name in client_map
                and getattr(self, client_map[client_name][1]) is None
            ):
                # Access property to trigger lazy initialization
                _ = client_map[client_name][0]

    # EventClient property and factory
    @property
    def event_client(self) -> EventClient:
        """
        Get or create the EventClient instance.

        Returns:
            EventClient: The event client for logging and event management
        """
        if self._event_client is None:
            self._event_client = self._create_event_client()
        return self._event_client

    @event_client.setter
    def event_client(self, client: EventClient) -> None:
        """Set the EventClient instance."""
        self._event_client = client

    def _create_event_client(self) -> EventClient:
        """
        Factory method for creating EventClient.

        Returns:
            EventClient: A new EventClient instance
        """
        # Use explicit config if provided
        if self.event_client_config is not None:
            return EventClient(config=self.event_client_config)

        # Build config from individual settings
        kwargs: dict[str, Any] = {}

        # Check for event_server_url override
        if hasattr(self, "event_server_url") and self.event_server_url is not None:
            kwargs["event_server_url"] = self.event_server_url

        # Check for name override (common pattern in existing code)
        if hasattr(self, "name"):
            kwargs["name"] = self.name

        # Create client (falls back to context if no overrides)
        return EventClient(**kwargs)

    # ResourceClient property and factory
    @property
    def resource_client(self) -> ResourceClient:
        """
        Get or create the ResourceClient instance.

        Returns:
            ResourceClient: The resource client for inventory tracking
        """
        if self._resource_client is None:
            self._resource_client = self._create_resource_client()
        return self._resource_client

    @resource_client.setter
    def resource_client(self, client: ResourceClient) -> None:
        """Set the ResourceClient instance."""
        self._resource_client = client

    def _create_resource_client(self) -> ResourceClient:
        """
        Factory method for creating ResourceClient.

        Returns:
            ResourceClient: A new ResourceClient instance
        """
        kwargs: dict[str, Any] = {}

        # Use explicit URL if provided
        if (
            hasattr(self, "resource_server_url")
            and self.resource_server_url is not None
        ):
            kwargs["resource_server_url"] = self.resource_server_url

        # Inject shared EventClient
        if self._event_client is not None:
            kwargs["event_client"] = self._event_client

        return ResourceClient(**kwargs)

    # DataClient property and factory
    @property
    def data_client(self) -> DataClient:
        """
        Get or create the DataClient instance.

        Returns:
            DataClient: The data client for data storage and retrieval
        """
        if self._data_client is None:
            self._data_client = self._create_data_client()
        return self._data_client

    @data_client.setter
    def data_client(self, client: DataClient) -> None:
        """Set the DataClient instance."""
        self._data_client = client

    def _create_data_client(self) -> DataClient:
        """
        Factory method for creating DataClient.

        Returns:
            DataClient: A new DataClient instance
        """
        kwargs: dict[str, Any] = {}

        # Use explicit URL if provided
        if hasattr(self, "data_server_url") and self.data_server_url is not None:
            kwargs["data_server_url"] = self.data_server_url

        # Use object storage settings if provided
        if (
            hasattr(self, "object_storage_settings")
            and self.object_storage_settings is not None
        ):
            kwargs["object_storage_settings"] = self.object_storage_settings

        return DataClient(**kwargs)

    # ExperimentClient property and factory
    @property
    def experiment_client(self) -> ExperimentClient:
        """
        Get or create the ExperimentClient instance.

        Returns:
            ExperimentClient: The experiment client for experiment management
        """
        if self._experiment_client is None:
            self._experiment_client = self._create_experiment_client()
        return self._experiment_client

    @experiment_client.setter
    def experiment_client(self, client: ExperimentClient) -> None:
        """Set the ExperimentClient instance."""
        self._experiment_client = client

    def _create_experiment_client(self) -> ExperimentClient:
        """
        Factory method for creating ExperimentClient.

        Returns:
            ExperimentClient: A new ExperimentClient instance
        """
        kwargs: dict[str, Any] = {}

        # Use explicit URL if provided
        if (
            hasattr(self, "experiment_server_url")
            and self.experiment_server_url is not None
        ):
            kwargs["experiment_server_url"] = self.experiment_server_url

        return ExperimentClient(**kwargs)

    # WorkcellClient property and factory
    @property
    def workcell_client(self) -> WorkcellClient:
        """
        Get or create the WorkcellClient instance.

        Returns:
            WorkcellClient: The workcell client for workflow coordination
        """
        if self._workcell_client is None:
            self._workcell_client = self._create_workcell_client()
        return self._workcell_client

    @workcell_client.setter
    def workcell_client(self, client: WorkcellClient) -> None:
        """Set the WorkcellClient instance."""
        self._workcell_client = client

    def _create_workcell_client(self) -> WorkcellClient:
        """
        Factory method for creating WorkcellClient.

        Returns:
            WorkcellClient: A new WorkcellClient instance
        """
        kwargs: dict[str, Any] = {}

        # Use explicit URL if provided
        if (
            hasattr(self, "workcell_server_url")
            and self.workcell_server_url is not None
        ):
            kwargs["workcell_server_url"] = self.workcell_server_url

        # Use working directory if provided
        if (
            hasattr(self, "workcell_working_directory")
            and self.workcell_working_directory is not None
        ):
            kwargs["working_directory"] = self.workcell_working_directory

        # Inject shared EventClient
        if self._event_client is not None:
            kwargs["event_client"] = self._event_client

        # Retry configuration
        if hasattr(self, "client_retry_enabled"):
            kwargs["retry"] = self.client_retry_enabled
        if hasattr(self, "client_retry_total"):
            kwargs["retry_total"] = self.client_retry_total
        if hasattr(self, "client_retry_backoff_factor"):
            kwargs["retry_backoff_factor"] = self.client_retry_backoff_factor
        if (
            hasattr(self, "client_retry_status_forcelist")
            and self.client_retry_status_forcelist is not None
        ):
            kwargs["retry_status_forcelist"] = self.client_retry_status_forcelist

        return WorkcellClient(**kwargs)

    # LocationClient property and factory
    @property
    def location_client(self) -> LocationClient:
        """
        Get or create the LocationClient instance.

        Returns:
            LocationClient: The location client for location management
        """
        if self._location_client is None:
            self._location_client = self._create_location_client()
        return self._location_client

    @location_client.setter
    def location_client(self, client: LocationClient) -> None:
        """Set the LocationClient instance."""
        self._location_client = client

    def _create_location_client(self) -> LocationClient:
        """
        Factory method for creating LocationClient.

        Returns:
            LocationClient: A new LocationClient instance
        """
        kwargs: dict[str, Any] = {}

        # Use explicit URL if provided
        if (
            hasattr(self, "location_server_url")
            and self.location_server_url is not None
        ):
            kwargs["location_server_url"] = self.location_server_url

        # Inject shared EventClient
        if self._event_client is not None:
            kwargs["event_client"] = self._event_client

        # Retry configuration
        if hasattr(self, "client_retry_enabled"):
            kwargs["retry"] = self.client_retry_enabled
        if hasattr(self, "client_retry_total"):
            kwargs["retry_total"] = self.client_retry_total
        if hasattr(self, "client_retry_backoff_factor"):
            kwargs["retry_backoff_factor"] = self.client_retry_backoff_factor
        if (
            hasattr(self, "client_retry_status_forcelist")
            and self.client_retry_status_forcelist is not None
        ):
            kwargs["retry_status_forcelist"] = self.client_retry_status_forcelist

        return LocationClient(**kwargs)

    # LabClient property and factory
    @property
    def lab_client(self) -> LabClient:
        """
        Get or create the LabClient instance.

        Returns:
            LabClient: The lab client for lab configuration
        """
        if self._lab_client is None:
            self._lab_client = self._create_lab_client()
        return self._lab_client

    @lab_client.setter
    def lab_client(self, client: LabClient) -> None:
        """Set the LabClient instance."""
        self._lab_client = client

    def _create_lab_client(self) -> LabClient:
        """
        Factory method for creating LabClient.

        Returns:
            LabClient: A new LabClient instance
        """
        kwargs: dict[str, Any] = {}

        # Use explicit URL if provided
        if hasattr(self, "lab_server_url") and self.lab_server_url is not None:
            kwargs["lab_server_url"] = self.lab_server_url

        return LabClient(**kwargs)

    # Convenience method for teardown (future use)
    def teardown_clients(self) -> None:
        """
        Clean up client resources.

        Currently a no-op, but provided for future enhancements
        where clients may need explicit cleanup (e.g., connection
        pools, background threads).

        This method can be called in shutdown handlers or context
        managers to ensure clean resource cleanup.
        """
        # Most clients are stateless REST consumers
        # EventClient has background threads that cleanup automatically
        # Future: Add explicit cleanup if needed
