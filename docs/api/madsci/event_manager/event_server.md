Module madsci.event_manager.event_server
========================================
Example Event Manager implementation using the new AbstractManagerBase class.

Classes
-------

`ArchiveEventsRequest(**data: Any)`
:   Request model for archiving events.
    
    Either event_ids or before_date must be provided to specify which events to archive.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `batch_size: int | None`
    :

    `before_date: datetime.datetime | None`
    :

    `event_ids: List[str] | None`
    :

    `model_config`
    :

    ### Methods

    `check_archive_params(self) ‑> madsci.event_manager.event_server.ArchiveEventsRequest`
    :   Validate that either event_ids or before_date is provided.

`ArchiveEventsResponse(**data: Any)`
:   Response model for archive operation.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `archived_count: int`
    :

    `message: str`
    :

    `model_config`
    :

`BackupRequest(**data: Any)`
:   Request model for backup creation.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `description: str | None`
    :

    `model_config`
    :

`BackupResponse(**data: Any)`
:   Response model for backup operation.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `backup_path: str`
    :

    `model_config`
    :

    `status: str`
    :

`BackupStatusResponse(**data: Any)`
:   Response model for backup status.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `available_backups: List[Dict[str, Any]]`
    :

    `backup_dir: str`
    :

    `backup_enabled: bool`
    :

    `model_config`
    :

`EventManager(settings: madsci.common.types.event_types.EventManagerSettings | None = None, db_connection: pymongo.synchronous.database.Database | None = None, mongo_handler: madsci.common.db_handlers.mongo_handler.MongoHandler | None = None, **kwargs: Any)`
:   Event Manager REST Server.
    
    Initialize the Event Manager.

    ### Ancestors (in MRO)

    * madsci.common.manager_base.AbstractManagerBase
    * madsci.client.client_mixin.MadsciClientMixin
    * typing.Generic
    * classy_fastapi.routable.Routable

    ### Class variables

    `SETTINGS_CLASS: type[madsci.common.types.base_types.MadsciBaseSettings] | None`
    :   Handles settings and configuration for the Event Manager.

    ### Methods

    `archive_events(self, request: madsci.event_manager.event_server.ArchiveEventsRequest = Body(PydanticUndefined)) ‑> madsci.event_manager.event_server.ArchiveEventsResponse`
    :   Archive (soft-delete) events.
        
        Events can be archived either by specific IDs or by date threshold.
        Archived events are excluded from default queries but can be retrieved
        using include_archived=True or the /events/archived endpoint.
        
        Args:
            request: Archive request containing event_ids and/or before_date
        
        Returns:
            Count of archived events

    `configure_app(self, app: fastapi.applications.FastAPI) ‑> None`
    :   Configure the FastAPI application with background retention task.
        
        Overrides the base class method to add retention task lifecycle management.

    `create_backup(self, request: madsci.event_manager.event_server.BackupRequest = Body(PydanticUndefined)) ‑> madsci.event_manager.event_server.BackupResponse`
    :   Create a one-time backup of all events.
        
        Uses the MongoDBBackupTool from madsci_common for consistent backup
        handling across all MADSci managers.
        
        Args:
            request: Backup request with optional description
        
        Returns:
            Backup file path and status

    `get_archived_events(self, number: int = Query(100), offset: int = Query(0)) ‑> Dict[str, madsci.common.types.event_types.Event]`
    :   Retrieve archived events.
        
        Args:
            number: Maximum number of events to return
            offset: Offset for pagination
        
        Returns:
            Dictionary of archived events

    `get_backup_status(self) ‑> madsci.event_manager.event_server.BackupStatusResponse`
    :   Get status of backups including list of available backups.
        
        Returns:
            Backup configuration and list of available backups

    `get_event(self, event_id: str) ‑> madsci.common.types.event_types.Event`
    :   Look up an event by event_id

    `get_events(self, number: int = Query(100), offset: int = Query(0), level: int | madsci.common.types.event_types.EventLogLevel = Query(0), start_time: datetime.datetime | None = Query(None), end_time: datetime.datetime | None = Query(None), include_archived: bool = Query(False)) ‑> Dict[str, madsci.common.types.event_types.Event]`
    :   Get events with enhanced filtering options.
        
        Args:
            number: Maximum number of events to return
            offset: Offset for pagination
            level: Minimum log level to include
            start_time: Filter events after this time
            end_time: Filter events before this time
            include_archived: Whether to include archived events (default False)
        
        Returns:
            Dictionary of events keyed by event_id

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

    `purge_archived_events(self, older_than_days: int = Query(365)) ‑> madsci.event_manager.event_server.PurgeEventsResponse`
    :   Permanently delete archived events older than threshold.
        
        This is a hard-delete operation. Events deleted this way cannot be recovered.
        Note: MongoDB TTL indexes also perform automatic hard-deletion based on
        the hard_delete_after_days setting.
        
        Args:
            older_than_days: Delete archived events older than this many days
        
        Returns:
            Count of deleted events

    `query_events(self, selector: Any = Body(PydanticUndefined)) ‑> Dict[str, madsci.common.types.event_types.Event]`
    :   Query events based on a selector. Note: this is a raw query, so be careful.

    `setup_logging(self) ‑> None`
    :   Setup logging for the event manager. Prevent recursive logging.

`PurgeEventsResponse(**data: Any)`
:   Response model for purge operation.
    
    Create a new model by parsing and validating input data from keyword arguments.
    
    Raises [`ValidationError`][pydantic_core.ValidationError] if the input data cannot be
    validated to form a valid model.
    
    `self` is explicitly positional-only to allow `self` as a field name.

    ### Ancestors (in MRO)

    * pydantic.main.BaseModel

    ### Class variables

    `deleted_count: int`
    :

    `message: str`
    :

    `model_config`
    :