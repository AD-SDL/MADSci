Module madsci.event_manager.event_server
========================================
Example Event Manager implementation using the new AbstractManagerBase class.

Classes
-------

`EventManager(settings: madsci.common.types.event_types.EventManagerSettings | None = None, definition: madsci.common.types.event_types.EventManagerDefinition | None = None, db_connection: pymongo.synchronous.database.Database | None = None, **kwargs: Any)`
:   Event Manager REST Server.

    Initialize the Event Manager.

    ### Ancestors (in MRO)

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Class variables

    `DEFINITION_CLASS: type[madsci.common.types.base_types.MadsciBaseModel] | None`
    :   Definition for a Squid Event Manager

    `ENABLE_ROOT_DEFINITION_ENDPOINT: bool`
    :

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :   Handles settings and configuration for the Event Manager.

    ### Methods

    `get_event(self, event_id: str) ‑> madsci.common.types.event_types.Event`
    :   Look up an event by event_id

    `get_events(self, number: int = 100, level: int | madsci.common.types.event_types.EventLogLevel = 0) ‑> Dict[str, madsci.common.types.event_types.Event]`
    :   Get the latest events

    `get_health(self) ‑> madsci.common.types.event_types.EventManagerHealth`
    :   Get the health status of the Event Manager.

    `get_session_utilization(self, start_time: str | None = None, end_time: str | None = None, csv_format: bool = Query(False), save_to_file: bool = Query(False), output_path: str | None = Query(None)) ‑> Dict[str, Any] | starlette.responses.Response`
    :   Generate comprehensive session-based utilization report.

    `get_user_utilization_report(self, start_time: str | None = None, end_time: str | None = None, csv_format: bool = Query(False), save_to_file: bool = Query(False), output_path: str | None = Query(None)) ‑> Dict[str, Any] | starlette.responses.Response`
    :   Generate detailed user utilization report based on workflow authors.

    `get_utilization_periods(self, start_time: str | None = None, end_time: str | None = None, analysis_type: str = Query(daily), user_timezone: str = Query(America/Chicago), include_users: bool = Query(True), csv_format: bool = Query(False), save_to_file: bool = Query(False), output_path: str | None = Query(None)) ‑> Dict[str, Any] | starlette.responses.Response`
    :   Generate time-series utilization analysis with periodic breakdowns.

    `initialize(self, **kwargs: Any) ‑> None`
    :   Initialize manager-specific components.

    `log_event(self, event: madsci.common.types.event_types.Event) ‑> madsci.common.types.event_types.Event`
    :   Create a new event.

    `query_events(self, selector: Any = Body(PydanticUndefined)) ‑> Dict[str, madsci.common.types.event_types.Event]`
    :   Query events based on a selector. Note: this is a raw query, so be careful.

    `setup_logging(self) ‑> None`
    :   Setup logging for the event manager. Prevent recursive logging.
