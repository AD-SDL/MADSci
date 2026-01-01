Module madsci.location_manager.location_server
==============================================
MADSci Location Manager using AbstractManagerBase.

Functions
---------

`create_app(settings: madsci.common.types.location_types.LocationManagerSettings | None = None, definition: madsci.common.types.location_types.LocationManagerDefinition | None = None) ‑> fastapi.applications.FastAPI`
:   Create and configure the FastAPI application.

`lifespan(app: fastapi.applications.FastAPI) ‑> AsyncGenerator[None, None]`
:   Manage the application lifespan.

Classes
-------

`LocationManager(settings: madsci.common.types.location_types.LocationManagerSettings | None = None, definition: madsci.common.types.location_types.LocationManagerDefinition | None = None, **kwargs: Any)`
:   MADSci Location Manager using the new AbstractManagerBase pattern.

    Initialize the LocationManager.

    ### Ancestors (in MRO)

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Class variables

    `DEFINITION_CLASS: type[madsci.common.types.base_types.MadsciBaseModel] | None`
    :   Definition for a LocationManager.

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :   Settings for the LocationManager.

    `transfer_planner: madsci.location_manager.transfer_planner.TransferPlanner | None`
    :

    ### Methods

    `add_location(self, location: madsci.common.types.location_types.Location) ‑> madsci.common.types.location_types.Location`
    :   Add a new location.

    `attach_resource(self, location_id: str, resource_id: str) ‑> madsci.common.types.location_types.Location`
    :   Attach a resource to a location.

    `delete_location(self, location_id: str) ‑> dict[str, str]`
    :   Delete a specific location by ID.

    `detach_resource(self, location_id: str) ‑> madsci.common.types.location_types.Location`
    :   Detach the resource from a location.

    `get_health(self) ‑> madsci.common.types.location_types.LocationManagerHealth`
    :   Get the health status of the Location Manager.

    `get_location_by_id(self, location_id: str) ‑> madsci.common.types.location_types.Location`
    :   Get a specific location by ID.

    `get_location_by_query(self, location_id: str | None = None, name: str | None = None) ‑> madsci.common.types.location_types.Location`
    :   Get a specific location by ID or name.

    `get_location_resources(self, location_id: str) ‑> madsci.common.types.resource_types.server_types.ResourceHierarchy`
    :   Get the resource hierarchy for resources currently at a specific location.

        Args:
            location_id: Location ID to query

        Returns:
            ResourceHierarchy: Hierarchy of resources at the location, or empty hierarchy if no attached resource

        Raises:
            HTTPException: If location not found

    `get_locations(self) ‑> list[madsci.common.types.location_types.Location]`
    :   Get all locations.

    `get_transfer_graph(self) ‑> dict[str, list[str]]`
    :   Get the current transfer graph as adjacency list.

        Returns:
            Dict mapping location IDs to lists of reachable location IDs

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

    `remove_representation(self, location_id: str, node_name: str) ‑> madsci.common.types.location_types.Location`
    :   Remove representations for a location for a specific node.

    `set_representations(self, location_id: str, node_name: str, representation_val: Annotated[Any, Body(PydanticUndefined)]) ‑> madsci.common.types.location_types.Location`
    :   Set representations for a location for a specific node.
