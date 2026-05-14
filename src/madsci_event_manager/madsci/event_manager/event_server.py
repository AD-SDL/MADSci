"""Example Event Manager implementation using the new AbstractManagerBase class."""

import asyncio
import warnings
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from classy_fastapi import delete, get, post
from fastapi import FastAPI, Query
from fastapi.exceptions import HTTPException
from fastapi.params import Body
from fastapi.responses import Response
from madsci.client.event_client import EventClient
from madsci.common.backup_tools import DocumentDBBackupTool
from madsci.common.db_handlers.document_storage_handler import (
    DocumentStorageHandler,
    PyDocumentStorageHandler,
)
from madsci.common.document_db_version_checker import DocumentDBVersionChecker
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.backup_types import DocumentDBBackupSettings
from madsci.common.types.document_db_migration_types import DocumentDBMigrationSettings
from madsci.common.types.event_types import (
    Event,
    EventLogLevel,
    EventManagerHealth,
    EventManagerSettings,
    EventType,
)
from madsci.event_manager.events_csv_exporter import CSVExporter
from madsci.event_manager.notifications import EmailAlerts
from madsci.event_manager.time_series_analyzer import TimeSeriesAnalyzer
from madsci.event_manager.utilization_analyzer import UtilizationAnalyzer
from pydantic import BaseModel, model_validator

if TYPE_CHECKING:
    from pymongo.synchronous.database import Database

# =============================================================================
# Request/Response Models for new endpoints
# =============================================================================


class ArchiveEventsRequest(BaseModel):
    """Request model for archiving events.

    Either event_ids or before_date must be provided to specify which events to archive.
    """

    event_ids: Optional[List[str]] = None
    before_date: Optional[datetime] = None
    batch_size: Optional[int] = None

    @model_validator(mode="after")
    def check_archive_params(self) -> "ArchiveEventsRequest":
        """Validate that either event_ids or before_date is provided."""
        if not self.event_ids and not self.before_date:
            raise ValueError("Either event_ids or before_date must be provided")
        return self


class ArchiveEventsResponse(BaseModel):
    """Response model for archive operation."""

    archived_count: int
    message: str


class PurgeEventsResponse(BaseModel):
    """Response model for purge operation."""

    deleted_count: int
    message: str


class BackupRequest(BaseModel):
    """Request model for backup creation."""

    description: Optional[str] = None


class BackupResponse(BaseModel):
    """Response model for backup operation."""

    backup_path: str
    status: str


class BackupStatusResponse(BaseModel):
    """Response model for backup status."""

    backup_enabled: bool
    backup_dir: str
    available_backups: List[Dict[str, Any]]


class EventManager(AbstractManagerBase[EventManagerSettings]):
    """Event Manager REST Server."""

    SETTINGS_CLASS = EventManagerSettings

    def __init__(
        self,
        settings: Optional[EventManagerSettings] = None,
        db_connection: Optional["Database"] = None,
        document_handler: Optional[DocumentStorageHandler] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Event Manager."""
        if db_connection is not None:
            warnings.warn(
                "The 'db_connection' parameter is deprecated. Use 'document_handler' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        # Store additional dependencies before calling super().__init__
        self._document_handler = document_handler
        self._db_connection = db_connection
        super().__init__(settings=settings, **kwargs)

        # Initialize database connection and collections
        self._setup_database()

    def initialize(self, **kwargs: Any) -> None:
        """Initialize manager-specific components."""
        super().initialize(**kwargs)

        # Skip version validation if an external handler/connection was provided (e.g., in tests)
        if self._document_handler is not None or self._db_connection is not None:
            # External connection provided, likely in test context - skip version validation
            self.logger.info(
                "External db_connection provided, skipping MongoDB version validation",
                event_type=EventType.MANAGER_START,
            )
            return

        self.logger.info(
            "Validating MongoDB schema version",
            event_type=EventType.MANAGER_START,
            database_name=self.settings.database_name,
        )

        schema_file_path = Path(__file__).parent / "schema.json"

        mig_cfg = DocumentDBMigrationSettings(database=self.settings.database_name)
        version_checker = DocumentDBVersionChecker(
            db_url=str(self.settings.document_db_url),
            database_name=self.settings.database_name,
            schema_file_path=str(schema_file_path),
            backup_dir=str(mig_cfg.backup_dir),
            logger=self.logger,
        )

        try:
            version_checker.validate_or_fail()
            self.logger.info(
                "MongoDB version validation completed successfully",
                event_type=EventType.MANAGER_START,
                database_name=self.settings.database_name,
            )
        except RuntimeError as e:
            self.logger.error(
                "Database version mismatch detected; server startup aborted",
                event_type=EventType.MANAGER_ERROR,
                database_name=self.settings.database_name,
            )
            raise e

    def setup_logging(self) -> None:
        """Setup logging for the event manager. Prevent recursive logging."""
        self._logger = EventClient(
            name=f"{self._resolve_name()}", event_server_url=None
        )
        self._logger.event_server = None

    def _setup_database(self) -> None:
        """Setup database connection and collections."""
        if self._document_handler is None:
            if self._db_connection is None:
                self._document_handler = PyDocumentStorageHandler.from_url(
                    str(self.settings.document_db_url),
                    self.settings.database_name,
                )
            else:
                # Legacy path: wrap an externally provided Database object
                self._document_handler = PyDocumentStorageHandler(self._db_connection)

        self.events = self._document_handler.get_collection(
            self.settings.collection_name
        )

        # Setup indexes for retention and query performance
        self._setup_indexes()

    def _setup_indexes(self) -> None:
        """Set up MongoDB indexes including TTL index for automatic hard-deletion."""
        try:
            # Standard indexes for query performance
            self.events.create_index("event_timestamp")
            self.events.create_index("log_level")
            self.events.create_index("archived")
            self.events.create_index([("archived", 1), ("archived_at", 1)])

            # TTL index for automatic hard-deletion of archived events
            # MongoDB will automatically delete documents where archived_at
            # is older than hard_delete_after_days
            if self.settings.retention_enabled:
                ttl_seconds = self.settings.hard_delete_after_days * 24 * 60 * 60

                # Note: TTL index only applies to documents where archived_at is set
                # Non-archived events (archived_at=None) are not affected
                # We need to check if the index already exists with a different TTL
                existing_indexes = self.events.index_information()
                ttl_index_name = "archived_at_1"

                if ttl_index_name in existing_indexes:
                    # Check if TTL needs updating
                    existing_ttl = existing_indexes[ttl_index_name].get(
                        "expireAfterSeconds"
                    )
                    if existing_ttl != ttl_seconds:
                        # Drop and recreate with new TTL
                        self.events.drop_index(ttl_index_name)
                        self.events.create_index(
                            "archived_at",
                            expireAfterSeconds=ttl_seconds,
                            partialFilterExpression={"archived": True},
                        )
                        self.logger.info(
                            "Updated TTL index for automatic hard-deletion",
                            event_type=EventType.MANAGER_START,
                            hard_delete_after_days=self.settings.hard_delete_after_days,
                        )
                else:
                    self.events.create_index(
                        "archived_at",
                        expireAfterSeconds=ttl_seconds,
                        partialFilterExpression={"archived": True},
                    )
                    self.logger.info(
                        "Created TTL index for automatic hard-deletion",
                        event_type=EventType.MANAGER_START,
                        hard_delete_after_days=self.settings.hard_delete_after_days,
                    )

        except Exception as e:
            self.logger.warning(
                "Failed to create event manager indexes",
                event_type=EventType.MANAGER_ERROR,
                error=str(e),
                exc_info=True,
            )

    # NOTE: OTEL instrumentation for event receipt lives in the existing /event
    # endpoint implementation further down in this file.

    def get_health(self) -> EventManagerHealth:
        """Get the health status of the Event Manager."""
        health = EventManagerHealth()
        base = super().get_health()

        try:
            # Test database connection
            health.db_connected = self._document_handler.ping()

            # Get total event count
            health.total_events = self.events.count_documents({})

            health.healthy = True
            health.description = "Event Manager is running normally"

        except Exception as e:
            health.healthy = False
            health.db_connected = False
            health.description = f"Database connection failed: {e!s}"

        health.otel_enabled = base.model_extra.get("otel.enabled")
        health.otel_exporter_type = base.model_extra.get("otel.exporter_type")
        health.otel_endpoint = base.model_extra.get("otel.endpoint")

        return health

    # ==========================================================================
    # Background Retention Task
    # ==========================================================================

    def configure_app(self, app: FastAPI) -> None:
        """Configure the FastAPI application with background retention task.

        Overrides the base class method to add retention task lifecycle management.
        """
        # Call parent configuration first (CORS, rate limiting, etc.)
        super().configure_app(app)

        # Store reference to retention task for cleanup
        self._retention_task: Optional[asyncio.Task[None]] = None

        @asynccontextmanager
        async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
            """Manage the lifecycle of background tasks."""
            # Startup: Start retention task if enabled
            if self.settings.retention_enabled:
                self._retention_task = asyncio.create_task(
                    self._run_retention_check_loop()
                )
                self.logger.info(
                    "Started automatic retention task",
                    event_type=EventType.MANAGER_START,
                    check_interval_hours=self.settings.retention_check_interval_hours,
                    soft_delete_after_days=self.settings.soft_delete_after_days,
                )
            yield
            # Shutdown: Cancel retention task if running
            if self._retention_task is not None:
                self._retention_task.cancel()
                with suppress(asyncio.CancelledError):
                    await self._retention_task
                self.logger.info(
                    "Stopped automatic retention task",
                    event_type=EventType.MANAGER_STOP,
                )

        # Set the lifespan on the app
        app.router.lifespan_context = lifespan

    async def _run_retention_check_loop(self) -> None:
        """Background task loop to enforce soft-delete retention policy.

        Note: Hard-deletion is handled automatically by MongoDB TTL index.
        This task only handles soft-deletion (archiving) of old events.
        """
        while True:
            try:
                archived_count = await self._archive_old_events()
                if archived_count > 0:
                    self.logger.info(
                        "Retention check completed",
                        event_type=EventType.MANAGER_HEALTH_CHECK,
                        archived_count=archived_count,
                    )
                else:
                    self.logger.debug("Retention check completed, no events to archive")
            except asyncio.CancelledError:
                # Task is being cancelled, exit gracefully
                raise
            except Exception as e:
                if self.settings.fail_on_retention_error:
                    self.logger.error(
                        "Retention check failed",
                        event_type=EventType.MANAGER_ERROR,
                        error=str(e),
                        exc_info=True,
                    )
                    raise
                self.logger.warning(
                    "Retention check failed",
                    event_type=EventType.MANAGER_ERROR,
                    error=str(e),
                    exc_info=True,
                )

            # Wait for next check interval
            await asyncio.sleep(self.settings.retention_check_interval_hours * 3600)

    async def _archive_old_events(self) -> int:
        """Archive old events in batches to prevent performance impact.

        Returns:
            Total number of events archived
        """
        soft_delete_cutoff = datetime.now(timezone.utc) - timedelta(
            days=self.settings.soft_delete_after_days
        )
        # Convert to ISO string to match MongoDB storage format
        soft_delete_cutoff_str = soft_delete_cutoff.isoformat()

        total_archived = 0
        batches_processed = 0
        batch_size = self.settings.archive_batch_size
        max_batches = self.settings.max_batches_per_run

        while True:
            # Check batch limit
            if max_batches > 0 and batches_processed >= max_batches:
                self.logger.info(
                    "Reached max batches limit, will continue next run",
                    event_type=EventType.MANAGER_HEALTH_CHECK,
                    batches_processed=batches_processed,
                    total_archived=total_archived,
                )
                break

            # Find batch of events to archive
            events_to_archive = list(
                self.events.find(
                    {
                        "event_timestamp": {"$lt": soft_delete_cutoff_str},
                        "archived": {"$ne": True},
                    },
                    {"_id": 1},
                ).limit(batch_size)
            )

            if not events_to_archive:
                break  # No more events to archive

            event_ids = [e["_id"] for e in events_to_archive]

            # Archive this batch
            result = self.events.update_many(
                {"_id": {"$in": event_ids}},
                {
                    "$set": {
                        "archived": True,
                        "archived_at": datetime.now(timezone.utc),
                    }
                },
            )

            total_archived += result.modified_count
            batches_processed += 1

            # Small delay between batches to reduce database load
            await asyncio.sleep(0.1)

        return total_archived

    @post("/event")
    async def log_event(self, event: Event) -> Event:
        """Create a new event."""
        with self.span(
            "event.receive",
            attributes={
                "event.level": event.log_level.name if event.log_level else "INFO",
                "event.type": event.event_type.value,
            },
        ):
            try:
                mongo_data = event.to_mongo()
                try:
                    self.events.insert_one(mongo_data)
                except Exception as insert_err:
                    # Handle duplicate key errors gracefully
                    if "DuplicateKeyError" not in type(insert_err).__name__:
                        raise
                    self.logger.warning(
                        "Duplicate event ID - skipping insert",
                        event_type=EventType.DATA_STORE,
                        event_id=event.event_id,
                    )
                    # Just continue - don't fail the request
            except Exception as e:
                self.logger.error(
                    "Failed to log event",
                    event_type=EventType.DATA_STORE,
                    error=str(e),
                    exc_info=True,
                )
                raise e

        if (
            event.alert or event.log_level >= self.settings.alert_level
        ) and self.settings.email_alerts:
            email_alerter = EmailAlerts(
                config=self.settings.email_alerts,
                logger=self.logger,
            )
            email_alerter.send_email_alerts(event)
        return event

    @get("/event/{event_id}")
    async def get_event(self, event_id: str) -> Event:
        """Look up an event by event_id"""
        event = self.events.find_one({"_id": event_id})
        if not event:
            self.logger.error(
                "Event not found",
                event_type=EventType.DATA_QUERY,
                event_id=event_id,
            )
            raise HTTPException(
                status_code=404, detail=f"Event with ID {event_id} not found"
            )
        return event

    @get("/events")
    async def get_events(
        self,
        number: int = Query(100, description="Maximum number of events to return"),
        offset: int = Query(0, description="Offset for pagination"),
        level: Union[int, EventLogLevel] = Query(  # noqa: B008
            0, description="Minimum log level to include"
        ),
        start_time: Optional[datetime] = Query(  # noqa: B008
            None, description="Filter events after this time (ISO format)"
        ),
        end_time: Optional[datetime] = Query(  # noqa: B008
            None, description="Filter events before this time (ISO format)"
        ),
        include_archived: bool = Query(
            False, description="Whether to include archived events"
        ),
    ) -> Dict[str, Event]:
        """Get events with enhanced filtering options.

        Args:
            number: Maximum number of events to return
            offset: Offset for pagination
            level: Minimum log level to include
            start_time: Filter events after this time
            end_time: Filter events before this time
            include_archived: Whether to include archived events (default False)

        Returns:
            Dictionary of events keyed by event_id
        """
        query: Dict[str, Any] = {"log_level": {"$gte": int(level)}}

        # Exclude archived events by default
        if not include_archived:
            query["archived"] = {"$ne": True}

        # Apply date range filters
        # Convert datetime to ISO string format to match MongoDB storage format
        # (Events are stored with ISO string timestamps via to_mongo())
        if start_time or end_time:
            query["event_timestamp"] = {}
            if start_time:
                query["event_timestamp"]["$gte"] = start_time.isoformat()
            if end_time:
                query["event_timestamp"]["$lte"] = end_time.isoformat()

        event_list = (
            self.events.find(query)
            .sort("event_timestamp", -1)
            .skip(offset)
            .limit(number)
            .to_list()
        )
        return {str(event["_id"]): Event.model_validate(event) for event in event_list}

    @post("/events/query")
    async def query_events(self, selector: Any = Body()) -> Dict[str, Event]:  # noqa: B008
        """Query events based on a selector. Note: this is a raw query, so be careful."""
        with self.span("event.query"):
            event_list = self.events.find(selector).to_list()
            return {event["_id"]: event for event in event_list}

    # ==========================================================================
    # Event Retention Endpoints
    # ==========================================================================

    @post("/events/archive")
    async def archive_events(
        self,
        request: ArchiveEventsRequest = Body(),  # noqa: B008
    ) -> ArchiveEventsResponse:
        """Archive (soft-delete) events.

        Events can be archived either by specific IDs or by date threshold.
        Archived events are excluded from default queries but can be retrieved
        using include_archived=True or the /events/archived endpoint.

        Args:
            request: Archive request containing event_ids and/or before_date

        Returns:
            Count of archived events
        """
        try:
            with self.span(
                "event.archive",
                attributes={
                    "archive.by_ids": bool(request.event_ids),
                    "archive.before_date": request.before_date.isoformat()
                    if request.before_date
                    else None,
                },
            ):
                query: Dict[str, Any] = {"archived": {"$ne": True}}

                # Build query based on request parameters
                # Note: Pydantic model_validator ensures at least one of these is set
                if request.event_ids:
                    query["_id"] = {"$in": request.event_ids}
                elif request.before_date:
                    # Convert datetime to ISO string format to match MongoDB storage format
                    # (Events are stored with ISO string timestamps via to_mongo())
                    query["event_timestamp"] = {"$lt": request.before_date.isoformat()}

                # Perform archive in batches to prevent performance impact
                batch_size = request.batch_size or self.settings.archive_batch_size
                total_archived = 0

                while True:
                    # Find batch of events to archive
                    events_to_archive = list(
                        self.events.find(query, {"_id": 1}).limit(batch_size)
                    )

                    if not events_to_archive:
                        break

                    event_ids = [e["_id"] for e in events_to_archive]

                    # Archive this batch
                    result = self.events.update_many(
                        {"_id": {"$in": event_ids}},
                        {
                            "$set": {
                                "archived": True,
                                "archived_at": datetime.now(timezone.utc),
                            }
                        },
                    )

                    total_archived += result.modified_count

                    # If archiving by IDs, we're done after one batch
                    if request.event_ids:
                        break

                return ArchiveEventsResponse(
                    archived_count=total_archived,
                    message=f"Successfully archived {total_archived} events",
                )

        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(
                "Failed to archive events",
                event_type=EventType.DATA_EXPORT,
                error=str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to archive events: {e!s}"
            ) from e

    @get("/events/archived")
    async def get_archived_events(
        self,
        number: int = Query(100, description="Maximum number of events to return"),
        offset: int = Query(0, description="Offset for pagination"),
    ) -> Dict[str, Event]:
        """Retrieve archived events.

        Args:
            number: Maximum number of events to return
            offset: Offset for pagination

        Returns:
            Dictionary of archived events
        """
        with self.span(
            "event.archived.list",
            attributes={"events.limit": number, "events.offset": offset},
        ):
            query = {"archived": True}
            event_list = (
                self.events.find(query)
                .sort("archived_at", -1)
                .skip(offset)
                .limit(number)
                .to_list()
            )
            return {
                str(event["_id"]): Event.model_validate(event) for event in event_list
            }

    @delete("/events/archived")
    async def purge_archived_events(
        self,
        older_than_days: int = Query(
            365, description="Delete archived events older than this many days"
        ),
    ) -> PurgeEventsResponse:
        """Permanently delete archived events older than threshold.

        This is a hard-delete operation. Events deleted this way cannot be recovered.
        Note: MongoDB TTL indexes also perform automatic hard-deletion based on
        the hard_delete_after_days setting.

        Args:
            older_than_days: Delete archived events older than this many days

        Returns:
            Count of deleted events
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

            result = self.events.delete_many(
                {
                    "archived": True,
                    "archived_at": {"$lt": cutoff_date},
                }
            )

            return PurgeEventsResponse(
                deleted_count=result.deleted_count,
                message=f"Permanently deleted {result.deleted_count} archived events older than {older_than_days} days",
            )

        except Exception as e:
            self.logger.error(
                "Failed to purge archived events",
                event_type=EventType.DATA_EXPORT,
                older_than_days=older_than_days,
                error=str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to purge archived events: {e!s}"
            ) from e

    # ==========================================================================
    # Backup Endpoints
    # ==========================================================================

    def _get_backup_dir(self) -> Path:
        """Resolve the backup directory path (sync helper for async methods)."""
        return Path(str(self.settings.backup_dir)).expanduser()

    def _backup_dir_exists(self, backup_dir: Path) -> bool:
        """Check if backup directory exists (sync helper for async methods)."""
        return backup_dir.exists()

    @post("/backup")
    async def create_backup(
        self,
        request: BackupRequest = Body(default_factory=BackupRequest),  # noqa: B008
    ) -> BackupResponse:
        """Create a one-time backup of all events.

        Uses the DocumentDBBackupTool from madsci_common for consistent backup
        handling across all MADSci managers.

        Args:
            request: Backup request with optional description

        Returns:
            Backup file path and status
        """
        try:
            with self.span(
                "event.backup.create",
                attributes={"backup.description": request.description},
            ):
                backup_dir = self._get_backup_dir()
                backup_settings = DocumentDBBackupSettings(
                    document_db_url=self.settings.document_db_url,
                    database=self.settings.database_name,
                    backup_dir=backup_dir,
                    max_backups=self.settings.backup_max_count,
                    validate_integrity=True,
                )

                backup_tool = DocumentDBBackupTool(
                    settings=backup_settings,
                    logger=self.logger,
                )

                description = request.description or "manual_backup"
                backup_path = backup_tool.create_backup(name_suffix=description)

                self.logger.info(
                    "Created backup",
                    event_type=EventType.DATA_EXPORT,
                    backup_path=str(backup_path),
                )

                return BackupResponse(
                    backup_path=str(backup_path),
                    status="completed",
                )

        except Exception as e:
            self.logger.error(
                "Failed to create backup",
                event_type=EventType.DATA_EXPORT,
                error=str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to create backup: {e!s}"
            ) from e

    @get("/backup/status")
    async def get_backup_status(self) -> BackupStatusResponse:
        """Get status of backups including list of available backups.

        Returns:
            Backup configuration and list of available backups
        """
        try:
            with self.span("event.backup.status"):
                backup_dir = self._get_backup_dir()
                available_backups: List[Dict[str, Any]] = []

                if self._backup_dir_exists(backup_dir):
                    backup_settings = DocumentDBBackupSettings(
                        document_db_url=self.settings.document_db_url,
                        database=self.settings.database_name,
                        backup_dir=backup_dir,
                        max_backups=self.settings.backup_max_count,
                    )

                    backup_tool = DocumentDBBackupTool(
                        settings=backup_settings,
                        logger=self.logger,
                    )

                    for backup_info in backup_tool.list_available_backups():
                        available_backups.append(
                            {
                                "path": str(backup_info.backup_path),
                                "created_at": backup_info.created_at.isoformat(),
                                "size_bytes": backup_info.backup_size,
                                "is_valid": backup_info.is_valid,
                            }
                        )

                return BackupStatusResponse(
                    backup_enabled=self.settings.backup_enabled,
                    backup_dir=str(backup_dir),
                    available_backups=available_backups,
                )

        except Exception as e:
            self.logger.error(
                "Failed to get backup status",
                event_type=EventType.DATA_QUERY,
                error=str(e),
                exc_info=True,
            )
            raise HTTPException(
                status_code=500, detail=f"Failed to get backup status: {e!s}"
            ) from e

    # Utilization endpoints (examples of more complex endpoints)

    @get("/utilization/sessions")
    async def get_session_utilization(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        csv_format: bool = Query(False, description="Return data in CSV format"),
        save_to_file: bool = Query(False, description="Save CSV to server filesystem"),
        output_path: Optional[str] = Query(
            None, description="Server path to save CSV files"
        ),
    ) -> Union[Dict[str, Any], Response]:
        """Generate comprehensive session-based utilization report."""
        analyzer = self._get_session_analyzer()
        if analyzer is None:
            return {"error": "Failed to create session analyzer"}

        try:
            # Parse time parameters and generate session-based report
            parsed_start, parsed_end = self._parse_session_time_parameters(
                start_time, end_time
            )
            report = analyzer.generate_session_based_report(parsed_start, parsed_end)

            # Handle CSV export if requested
            if csv_format:
                csv_result = CSVExporter.handle_session_csv_export(
                    report, save_to_file, output_path
                )

                # Return error if CSV processing failed
                if "error" in csv_result:
                    return csv_result

                # Return Response object for download or JSON for file save
                if csv_result.get("is_download"):
                    return Response(
                        content=csv_result["csv_content"],
                        media_type="text/csv",
                        headers={
                            "Content-Disposition": "attachment; filename=session_utilization_report.csv"
                        },
                    )

                # File save results as JSON
                return csv_result

            # Default JSON response
            return report

        except Exception as e:
            self.logger.error(
                "Error generating session utilization",
                event_type=EventType.DATA_QUERY,
                error=str(e),
                exc_info=True,
            )
            return {"error": f"Failed to generate report: {e!s}"}

    def _get_session_analyzer(self) -> Optional[UtilizationAnalyzer]:
        """Create session analyzer on-demand."""
        try:
            return UtilizationAnalyzer(self.events)
        except Exception as e:
            self.logger.error(
                "Failed to create session analyzer",
                event_type=EventType.DATA_QUERY,
                error=str(e),
                exc_info=True,
            )
            return None

    def _parse_session_time_parameters(
        self, start_time: Optional[str], end_time: Optional[str]
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Parse time parameters for session utilization reports."""
        parsed_start = None
        parsed_end = None

        if start_time:
            parsed_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if end_time:
            parsed_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        return parsed_start, parsed_end

    @get("/utilization/periods")
    async def get_utilization_periods(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        analysis_type: str = Query(
            "daily", description="Analysis type: hourly, daily, weekly, monthly"
        ),
        user_timezone: str = Query(
            "America/Chicago", description="Timezone for day boundaries"
        ),
        include_users: bool = Query(True, description="Include user utilization data"),
        csv_format: bool = Query(False, description="Return data in CSV format"),
        save_to_file: bool = Query(False, description="Save CSV to server filesystem"),
        output_path: Optional[str] = Query(
            None, description="Server path to save CSV files"
        ),
    ) -> Union[Dict[str, Any], Response]:
        """Generate time-series utilization analysis with periodic breakdowns."""
        try:
            # Create analyzer and time-series analyzer
            analyzer = self._get_session_analyzer()
            if analyzer is None:
                return {"error": "Failed to create session analyzer"}

            time_series_analyzer = TimeSeriesAnalyzer(analyzer)

            # Generate report
            report = time_series_analyzer.generate_utilization_report_with_times(
                start_time, end_time, analysis_type, user_timezone
            )

            # Add user utilization if requested
            if include_users and report and "error" not in report:
                try:
                    time_series_analyzer.add_user_utilization_to_report(report)
                except Exception as e:
                    self.logger.warning(
                        "Failed to add user utilization",
                        event_type=EventType.DATA_QUERY,
                        error=str(e),
                        exc_info=True,
                    )

            # Handle CSV export if requested
            if csv_format and report and "error" not in report:
                csv_result = CSVExporter.handle_api_csv_export(
                    report, save_to_file, output_path
                )

                # Return error if CSV processing failed
                if "error" in csv_result:
                    return csv_result

                # Return Response object for download or JSON for file save
                if csv_result.get("is_download"):
                    return Response(
                        content=csv_result["csv_content"],
                        media_type="text/csv",
                        headers={
                            "Content-Disposition": "attachment; filename=utilization_periods_report.csv"
                        },
                    )

                # File save results as JSON
                return csv_result

            # Default JSON response
            return report

        except Exception as e:
            self.logger.error(
                "Error generating utilization periods report",
                event_type=EventType.DATA_QUERY,
                error=str(e),
                exc_info=True,
            )
            return {"error": f"Failed to generate report: {e!s}"}

    @get("/utilization/user")
    async def get_user_utilization_report(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        csv_format: bool = Query(False, description="Return data in CSV format"),
        save_to_file: bool = Query(False, description="Save CSV to server filesystem"),
        output_path: Optional[str] = Query(
            None, description="Server path to save CSV files"
        ),
    ) -> Union[Dict[str, Any], Response]:
        """Generate detailed user utilization report based on workflow authors."""
        try:
            # Create analyzer
            analyzer = self._get_session_analyzer()
            if analyzer is None:
                return {"error": "Failed to create session analyzer"}

            # Parse time parameters and generate user utilization report
            parsed_start, parsed_end = self._parse_session_time_parameters(
                start_time, end_time
            )
            report = analyzer.generate_user_utilization_report(parsed_start, parsed_end)

            # Handle CSV export if requested
            if csv_format and report and "error" not in report:
                csv_result = CSVExporter.handle_user_csv_export(
                    report, save_to_file, output_path
                )

                # Return error if CSV processing failed
                if "error" in csv_result:
                    return csv_result

                # Return Response object for download or JSON for file save
                if csv_result.get("is_download"):
                    return Response(
                        content=csv_result["csv_content"],
                        media_type="text/csv",
                        headers={
                            "Content-Disposition": "attachment; filename=user_utilization_report.csv"
                        },
                    )

                # File save results as JSON
                return csv_result

            # Default JSON response
            return report

        except Exception as e:
            self.logger.error(
                "Error generating user utilization report",
                event_type=EventType.DATA_QUERY,
                error=str(e),
                exc_info=True,
            )
            return {"error": f"Failed to generate report: {e!s}"}


# Main entry point for running the server
if __name__ == "__main__":
    manager = EventManager()
    manager.run_server()
