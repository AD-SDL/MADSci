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

    ### Ancestors (in MRO)

    * madsci.client.http.DualModeClientMixin

    ### Class variables

    `location_server_url: pydantic.networks.AnyUrl | None`
    :

    ### Instance variables

    `session: httpx.Client`
    :   Backward-compatible accessor for the underlying HTTP client.

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

    `async_add_location(self, location: madsci.common.types.location_types.Location, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Add a location asynchronously.

    `async_attach_resource(self, location_name: str, resource_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Attach a resource to a location asynchronously.

    `async_create_location_from_template(self, location_name: str, template_name: str, node_bindings: dict[str, str] | None = None, representation_overrides: dict[str, dict[str, typing.Any]] | None = None, resource_template_overrides: dict[str, typing.Any] | None = None, description: str | None = None, allow_transfers: bool | None = None, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Create a location from a LocationTemplate asynchronously.

    `async_create_location_template(self, template: madsci.common.types.location_types.LocationTemplate, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Create a new location template asynchronously.

    `async_create_representation_template(self, template: madsci.common.types.location_types.LocationRepresentationTemplate, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Create a new representation template asynchronously.

    `async_delete_location(self, location_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a specific location by name asynchronously.

    `async_delete_location_template(self, template_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a location template by name asynchronously.

    `async_delete_representation_template(self, template_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a representation template by name asynchronously.

    `async_detach_resource(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Detach the resource from a location asynchronously.

    `async_export_locations(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.Location]`
    :   Export all locations from the server asynchronously.

    `async_get_location(self, location_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get details of a specific location by ID asynchronously.

    `async_get_location_by_name(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get a specific location by name asynchronously.

    `async_get_location_resources(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy`
    :   Get the resource hierarchy for resources at a specific location asynchronously.

    `async_get_location_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Get a location template by name asynchronously.

    `async_get_location_templates(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.LocationTemplate]`
    :   Get all location templates asynchronously.

    `async_get_locations(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.Location]`
    :   Get all locations asynchronously.

    `async_get_representation_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Get a representation template by name asynchronously.

    `async_get_representation_templates(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.LocationRepresentationTemplate]`
    :   Get all representation templates asynchronously.

    `async_get_transfer_graph(self, timeout: float | None = None) ‑> dict[str, list[str]]`
    :   Get the current transfer graph as adjacency list asynchronously.

    `async_import_locations(self, location_file_path: pathlib.Path | None = None, locations: list[madsci.common.types.location_types.Location] | None = None, overwrite: bool = False, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationImportResult`
    :   Import multiple locations from a file or a list asynchronously.
        
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

    `async_plan_transfer(self, source_location_id: str, target_location_id: str, resource_id: str | None = None, timeout: float | None = None) ‑> dict[str, typing.Any]`
    :   Plan a transfer from source to target location asynchronously.

    `async_remove_representation(self, location_name: str, node_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Remove representations for a location for a specific node asynchronously.

    `async_set_representation(self, location_name: str, node_name: str, representation: Any, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Set a representation for a location for a specific node asynchronously.

    `attach_resource(self, location_name: str, resource_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Attach a resource to a location.
        
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

    `create_location_from_template(self, location_name: str, template_name: str, node_bindings: dict[str, str] | None = None, representation_overrides: dict[str, dict[str, typing.Any]] | None = None, resource_template_overrides: dict[str, typing.Any] | None = None, description: str | None = None, allow_transfers: bool | None = None, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Create a location from a LocationTemplate.

    `create_location_template(self, template: madsci.common.types.location_types.LocationTemplate, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Create a new location template.

    `create_representation_template(self, template: madsci.common.types.location_types.LocationRepresentationTemplate, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Create a new representation template.

    `delete_location(self, location_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a specific location by name.
        
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

    `delete_location_template(self, template_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a location template by name.

    `delete_representation_template(self, template_name: str, timeout: float | None = None) ‑> dict[str, str]`
    :   Delete a representation template by name.

    `detach_resource(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Detach the resource from a location.
        
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

    `export_locations(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.Location]`
    :   Export all locations from the server.
        
        Parameters
        ----------
        timeout : Optional[float]
            Optional timeout override in seconds. If None, uses config.timeout_default.
        
        Returns
        -------
        list[Location]
            All locations managed by the location server.

    `get_location(self, location_id: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get details of a specific location by ID.
        
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

    `get_location_resources(self, location_name: str, timeout: float | None = None) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy`
    :   Get the resource hierarchy for resources currently at a specific location.
        
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

    `get_location_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Get a location template by name.

    `get_location_templates(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.LocationTemplate]`
    :   Get all location templates.

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

    `get_representation_template(self, template_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Get a representation template by name.

    `get_representation_templates(self, timeout: float | None = None) ‑> list[madsci.common.types.location_types.LocationRepresentationTemplate]`
    :   Get all representation templates.

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

    `import_locations(self, location_file_path: pathlib.Path | None = None, locations: list[madsci.common.types.location_types.Location] | None = None, overwrite: bool = False, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationImportResult`
    :   Import multiple locations from a file or a list.
        
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

    `init_location_template(self, template_name: str, representation_templates: dict[str, str] | None = None, resource_template_name: str | None = None, resource_template_overrides: dict[str, typing.Any] | None = None, default_allow_transfers: bool = True, tags: list[str] | None = None, created_by: str | None = None, version: str = '1.0.0', description: str | None = None, timeout: float | None = None) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Idempotent init: get-or-create, version-update for a location template.
        
        Retries with exponential backoff on connection errors to tolerate
        transient unavailability of the location manager during startup.

    `init_representation_template(self, template_name: str, default_values: dict[str, typing.Any] | None = None, schema: dict[str, typing.Any] | None = None, required_overrides: list[str] | None = None, tags: list[str] | None = None, created_by: str | None = None, version: str = '1.0.0', description: str | None = None, timeout: float | None = None, schema_def: dict[str, typing.Any] | None = None) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Idempotent init: get-or-create, version-update for a representation template.
        
        Retries with exponential backoff on connection errors to tolerate
        transient unavailability of the location manager during startup.
        
        The ``schema`` parameter is deprecated; use ``schema_def`` instead.
        If both are provided, ``schema_def`` takes precedence.

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

    `remove_representation(self, location_name: str, node_name: str, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Remove representations for a location for a specific node.
        
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

    `set_representation(self, location_name: str, node_name: str, representation: Any, timeout: float | None = None) ‑> madsci.common.types.location_types.Location`
    :   Set a representation for a location for a specific node.
        
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