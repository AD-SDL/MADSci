Module madsci.client.location_client
====================================
Client for performing location management actions.

Classes
-------

`LocationClient(location_server_url: str | pydantic.networks.AnyUrl | None = None, event_client: madsci.client.event_client.EventClient | None = None, config: madsci.common.types.client_types.LocationClientConfig | None = None)`
:   A client for interacting with the Location Manager to perform location operations.

    Initialize the LocationClient.

    Parameters
    ----------
    location_server_url : Optional[Union[str, AnyUrl]]
        The URL of the location server. If None, will try to get from context.
    event_client : Optional[EventClient]
        Event client for logging. If not provided, a new one will be created.
    config : Optional[LocationClientConfig]
        Client configuration for retry and timeout settings. If not provided, uses default LocationClientConfig.

    ### Class variables

    `location_server_url: pydantic.networks.AnyUrl | None`
    :

    ### Methods

    `add_location(self, location: madsci.common.types.location_types.Location, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Add a location.

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

    `attach_resource(self, location_id: str, resource_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Attach a resource to a location.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        resource_id : str
            The ID of the resource to attach.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        Location
            The updated location.

    `delete_location(self, location_id: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a specific location.

        Parameters
        ----------
        location_id : str
            The ID of the location to delete.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        dict[str, str]
            A message confirming deletion.

    `detach_resource(self, location_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Detach the resource from a location.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        Location
            The updated location.

    `get_location(self, location_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get details of a specific location.

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

    `get_location_by_name(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get a specific location by name.

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

    `get_location_resources(self, location_id: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy`
    :   Get the resource hierarchy for resources currently at a specific location.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        ResourceHierarchy
            Hierarchy of resources at the location, or empty hierarchy if no attached resource.

    `get_locations(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.Location]`
    :   Get all locations.

        Parameters
        ----------
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        list[Location]
            A list of all locations.

    `get_transfer_graph(self, timeout: float | None = None) ‑> dict[str, list[str]]`
    :   Get the current transfer graph as adjacency list.

        Parameters
        ----------
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        dict[str, list[str]]
            Transfer graph as adjacency list mapping source location IDs to
            lists of reachable destination location IDs.

    `plan_transfer(self, source_location_id: str, target_location_id: str, resource_id: str | None = None, timeout: float | None = None) ‑> dict[str, typing.Any]`
    :   Plan a transfer from source to target location.

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

    `remove_representation(self, location_id: str, node_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Remove representations for a location for a specific node.

        Parameters
        ----------
        location_id : str
            The ID of the location.
        node_name : str
            The name of the node.
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.

        Returns
        -------
        Location
            The updated location.

    `set_representations(self, location_id: str, node_name: str, representation: Any, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Set a representation for a location for a specific node.

        Parameters
        ----------
        location_id : str
            The ID of the location.
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
