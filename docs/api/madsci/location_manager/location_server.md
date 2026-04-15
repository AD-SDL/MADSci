Module madsci.location_manager.location_server
==============================================
MADSci Location Manager using AbstractManagerBase.

Functions
---------

`create_app(settings: madsci.common.types.location_types.LocationManagerSettings | None = None, document_handler: madsci.common.db_handlers.document_storage_handler.DocumentStorageHandler | None = None) ‑> fastapi.applications.FastAPI`
:   Create and configure the FastAPI application.

Classes
-------

`LocationManager(settings: madsci.common.types.location_types.LocationManagerSettings | None = None, redis_connection: Any | None = None, cache_handler: madsci.common.db_handlers.cache_handler.CacheHandler | None = None, document_handler: madsci.common.db_handlers.document_storage_handler.DocumentStorageHandler | None = None, **kwargs: Any)`
:   MADSci Location Manager using the new AbstractManagerBase pattern.
    
    This class is decorated with @ownership_class() which automatically
    establishes ownership context for all public methods, eliminating the
    need for manual `with ownership_context():` blocks in each endpoint.
    
    Initialize the LocationManager.

    ### Ancestors (in MRO)

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Class variables

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :   Settings for the LocationManager.

    `transfer_planner: madsci.location_manager.transfer_planner.TransferPlanner | None`
    :

    ### Instance variables

    `ownership_info: madsci.common.types.auth_types.OwnershipInfo`
    :   Get the current OwnershipInfo.

    ### Methods

    `add_location(self, location: madsci.common.types.location_types.Location) ‑> madsci.common.types.location_types.Location`
    :   Add a new location.

    `attach_resource(self, location_name: str, resource_id: str) ‑> madsci.common.types.location_types.Location`
    :   Attach a resource to a location.

    `close(self) ‑> None`
    :   Override to close state handler and release DB connections.

    `create_location_from_template(self, request: madsci.common.types.location_types.CreateLocationFromTemplateRequest) ‑> madsci.common.types.location_types.Location`
    :   Create a new location by instantiating a LocationTemplate.
        
        Requires node bindings to map abstract roles to concrete node instance names.
        Representation data is merged from template defaults + overrides.

    `create_location_template(self, template: madsci.common.types.location_types.LocationTemplate) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Create a new location template.

    `create_representation_template(self, template: madsci.common.types.location_types.LocationRepresentationTemplate) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Create a new representation template.

    `create_server(self, **kwargs: Any) ‑> fastapi.applications.FastAPI`
    :   Create the FastAPI server with the reconciliation lifespan.
        
        Overrides the base class to ensure the periodic reconciliation loop
        is always started, regardless of whether the server is launched via
        ``run_server()`` or ``create_app()``.

    `delete_location(self, location_name: str) ‑> dict[str, str]`
    :   Delete a specific location by name.

    `delete_location_template(self, template_name: str) ‑> dict[str, str]`
    :   Delete a location template by name.

    `delete_representation_template(self, template_name: str) ‑> dict[str, str]`
    :   Delete a representation template by name.

    `detach_resource(self, location_name: str) ‑> madsci.common.types.location_types.Location`
    :   Detach the resource from a location.

    `export_locations(self) ‑> list[madsci.common.types.location_types.Location]`
    :   Export all locations as a JSON list.
        
        Semantically distinct from GET /locations for import/export workflows.

    `get_detailed_transfer_graph(self) ‑> madsci.common.types.location_types.TransferGraphDetailedResponse`
    :   Get the current transfer graph with detailed edge information.

    `get_health(self) ‑> madsci.common.types.location_types.LocationManagerHealth`
    :   Get the health status of the Location Manager.

    `get_location(self, location_name: str) ‑> madsci.common.types.location_types.Location`
    :   Get a specific location by name.

    `get_location_by_query(self, location_id: str | None = None, name: str | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get a specific location by ID or name.

    `get_location_resources(self, location_name: str) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy | None`
    :   Get the resource hierarchy for resources currently at a specific location.
        
        Args:
            location_name: Location name to query
        
        Returns:
            ResourceHierarchy: Hierarchy of resources at the location, or empty hierarchy if no attached resource
        
        Raises:
            HTTPException: If location not found

    `get_location_template(self, template_name: str) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Get a location template by name.

    `get_location_templates(self) ‑> list[madsci.common.types.location_types.LocationTemplate]`
    :   Get all location templates.

    `get_locations(self, managed_by: madsci.common.types.location_types.LocationManagement | None = None) ‑> list[madsci.common.types.location_types.Location]`
    :   Get all locations, optionally filtered by management type.

    `get_reconciliation_status(self) ‑> dict[str, typing.Any]`
    :   Get the status of the last reconciliation cycle.

    `get_representation_template(self, template_name: str) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Get a representation template by name.

    `get_representation_templates(self) ‑> list[madsci.common.types.location_types.LocationRepresentationTemplate]`
    :   Get all representation templates.

    `get_transfer_graph(self) ‑> dict[str, list[str]]`
    :   Get the current transfer graph as adjacency list.
        
        Returns:
            Dict mapping location IDs to lists of reachable location IDs

    `import_locations(self, locations: list[madsci.common.types.location_types.Location], overwrite: bool = False) ‑> madsci.common.types.location_types.LocationImportResult`
    :   Import multiple locations in bulk.
        
        Parameters
        ----------
        locations:
            List of Location objects to import.
        overwrite:
            If True, overwrite existing locations with the same name.
            If False (default), skip duplicates.
        
        Returns
        -------
        LocationImportResult with counts and imported locations.

    `init_location(self, location: madsci.common.types.location_types.Location) ‑> madsci.common.types.location_types.Location`
    :   Idempotent init: get-or-create a location.
        
        If a location with the given name exists, return it unchanged.
        If it does not exist, create it with lazy resource resolution.

    `init_location_template(self, template: madsci.common.types.location_types.LocationTemplate) ‑> madsci.common.types.location_types.LocationTemplate`
    :   Idempotent init: get-or-create, version-update.
        
        If template exists with same version, return it unchanged.
        If template exists with different version, update and return.
        If template doesn't exist, create and return.

    `init_representation_template(self, template: madsci.common.types.location_types.LocationRepresentationTemplate) ‑> madsci.common.types.location_types.LocationRepresentationTemplate`
    :   Idempotent init: get-or-create, version-update.
        
        If template exists with same version, return it unchanged.
        If template exists with different version, update and return.
        If template doesn't exist, create and return.

    `initialize(self, **_kwargs: Any) ‑> None`
    :   Initialize manager-specific components.

    `plan_transfer(self, source_location_id: str, target_location_id: str) ‑> madsci.common.types.workflow_types.WorkflowDefinition`
    :   Plan a transfer workflow from source to target.
        
        Args:
            source_location_id: Source location ID
            target_location_id: Target location ID
        
        Returns:
            Composite workflow definition to execute the transfer
        
        Raises:
            HTTPException: If no transfer path exists

    `remove_representation(self, location_name: str, node_name: str) ‑> madsci.common.types.location_types.Location`
    :   Remove representations for a location for a specific node.

    `set_representation(self, location_name: str, node_name: str, representation_val: Annotated[Any, Body(PydanticUndefined)]) ‑> madsci.common.types.location_types.Location`
    :   Set representations for a location for a specific node.

    `trigger_reconcile(self) ‑> dict[str, typing.Any]`
    :   Manually trigger reconciliation of unresolved template references.