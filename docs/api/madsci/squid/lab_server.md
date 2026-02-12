Module madsci.squid.lab_server
==============================
Lab Manager implementation using the new AbstractManagerBase class.

Classes
-------

`LabManager(settings: madsci.common.types.lab_types.LabManagerSettings | None = None, definition: madsci.common.types.lab_types.LabManagerDefinition | None = None, **kwargs: Any)`
:   Lab Manager REST Server.

    Initialize the Lab Manager.

    ### Ancestors (in MRO)

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Class variables

    `DEFINITION_CLASS: type[madsci.common.types.base_types.MadsciBaseModel] | None`
    :   Definition for a MADSci Lab Manager.

    `ENABLE_ROOT_DEFINITION_ENDPOINT: bool`
    :

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :   Settings for the MADSci Lab.

    ### Methods

    `check_each_managers_health(self, manager_healths: dict, manager_urls: dict) ‑> tuple[int, int]`
    :   Checks the health of each manager given their URLs.

    `create_server(self, **kwargs: Any) ‑> fastapi.applications.FastAPI`
    :   Create the FastAPI server application with proper route order.

    `get_context(self) ‑> madsci.common.types.context_types.MadsciContext`
    :   Get the context of the lab server.

    `get_lab_health(self) ‑> madsci.common.types.lab_types.LabHealth`
    :   Get the health status of the entire lab, including all managers.

    `lab_health_endpoint(self) ‑> madsci.common.types.lab_types.LabHealth`
    :   Health check endpoint for the entire lab.
