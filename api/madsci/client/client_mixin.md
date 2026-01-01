Module madsci.client.client_mixin
=================================
Mixin class for managing MADSci client lifecycle.

This module provides a reusable mixin that handles client initialization,
configuration, and lifecycle management across MADSci components.

Classes
-------

`MadsciClientMixin()`
:   Mixin for managing MADSci client lifecycle.

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

    ### Descendants

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.node_module.abstract_node_module.AbstractNode

    ### Class variables

    `OPTIONAL_CLIENTS: ClassVar[list[str]]`
    :

    `REQUIRED_CLIENTS: ClassVar[list[str]]`
    :

    `client_retry_backoff_factor: float`
    :

    `client_retry_enabled: bool`
    :

    `client_retry_status_forcelist: list[int] | None`
    :

    `client_retry_total: int`
    :

    `data_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `event_client_config: madsci.common.types.event_types.EventClientConfig | None`
    :

    `event_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `experiment_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `lab_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `location_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `object_storage_settings: madsci.common.types.datapoint_types.ObjectStorageSettings | None`
    :

    `resource_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `workcell_server_url: str | pydantic.networks.AnyUrl | None`
    :

    `workcell_working_directory: str`
    :

    ### Instance variables

    `data_client: madsci.client.data_client.DataClient`
    :   Get or create the DataClient instance.

        Returns:
            DataClient: The data client for data storage and retrieval

    `event_client: madsci.client.event_client.EventClient`
    :   Get or create the EventClient instance.

        Returns:
            EventClient: The event client for logging and event management

    `experiment_client: madsci.client.experiment_client.ExperimentClient`
    :   Get or create the ExperimentClient instance.

        Returns:
            ExperimentClient: The experiment client for experiment management

    `lab_client: madsci.client.lab_client.LabClient`
    :   Get or create the LabClient instance.

        Returns:
            LabClient: The lab client for lab configuration

    `location_client: madsci.client.location_client.LocationClient`
    :   Get or create the LocationClient instance.

        Returns:
            LocationClient: The location client for location management

    `resource_client: madsci.client.resource_client.ResourceClient`
    :   Get or create the ResourceClient instance.

        Returns:
            ResourceClient: The resource client for inventory tracking

    `workcell_client: madsci.client.workcell_client.WorkcellClient`
    :   Get or create the WorkcellClient instance.

        Returns:
            WorkcellClient: The workcell client for workflow coordination

    ### Methods

    `setup_clients(self, clients: list[str] | None = None, event_client: madsci.client.event_client.EventClient | None = None, resource_client: madsci.client.resource_client.ResourceClient | None = None, data_client: madsci.client.data_client.DataClient | None = None, experiment_client: madsci.client.experiment_client.ExperimentClient | None = None, workcell_client: madsci.client.workcell_client.WorkcellClient | None = None, location_client: madsci.client.location_client.LocationClient | None = None, lab_client: madsci.client.lab_client.LabClient | None = None) ‑> None`
    :   Initialize specified clients.

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

    `teardown_clients(self) ‑> None`
    :   Clean up client resources.

        Currently a no-op, but provided for future enhancements
        where clients may need explicit cleanup (e.g., connection
        pools, background threads).

        This method can be called in shutdown handlers or context
        managers to ensure clean resource cleanup.
