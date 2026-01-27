Module madsci.data_manager.data_server
======================================
Data Manager implementation using the new AbstractManagerBase class.

Classes
-------

`DataManager(settings: madsci.common.types.datapoint_types.DataManagerSettings | None = None, definition: madsci.common.types.datapoint_types.DataManagerDefinition | None = None, object_storage_settings: madsci.common.types.datapoint_types.ObjectStorageSettings | None = None, db_client: pymongo.synchronous.mongo_client.MongoClient | None = None, **kwargs: Any)`
:   Data Manager REST Server.

    Initialize the Data Manager.

    ### Ancestors (in MRO)

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Class variables

    `DEFINITION_CLASS: type[madsci.common.types.base_types.MadsciBaseModel] | None`
    :   Definition for a Squid Data Manager.

        Attributes:
            manager_type: The type of the event manager.
            host: The hostname or IP address of the Data Manager server.
            port: The port number of the Data Manager server.
            db_url: The URL of the database used by the Data Manager.

    `ENABLE_ROOT_DEFINITION_ENDPOINT: bool`
    :

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :   Settings for the MADSci Data Manager.

    ### Methods

    `create_datapoint(self, datapoint: Annotated[str, Form(PydanticUndefined)], files: list[fastapi.datastructures.UploadFile] = []) ‑> Any`
    :   Create a new datapoint.

    `get_datapoint(self, datapoint_id: str) ‑> Any`
    :   Look up a datapoint by datapoint_id

    `get_datapoint_value(self, datapoint_id: str) ‑> starlette.responses.Response`
    :   Returns a specific data point's value. If this is a file, it will return the file.

    `get_datapoints(self, number: int = 100) ‑> Dict[str, Any]`
    :   Get the latest datapoints

    `get_health(self) ‑> madsci.common.types.datapoint_types.DataManagerHealth`
    :   Get the health status of the Data Manager.

    `initialize(self, **kwargs: Any) ‑> None`
    :   Initialize manager-specific components.

    `query_datapoints(self, selector: Any = Body(PydanticUndefined)) ‑> Dict[str, Any]`
    :   Query datapoints based on a selector. Note: this is a raw query, so be careful.
