"""Example Event Manager implementation using the new AbstractManagerBase class."""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple, Union

import pymongo
from classy_fastapi import get, post
from fastapi import Query
from fastapi.exceptions import HTTPException
from fastapi.params import Body
from fastapi.responses import Response
from madsci.client.event_client import EventClient
from madsci.common.manager_base import AbstractManagerBase
from madsci.common.types.event_types import (
    Event,
    EventLogLevel,
    EventManagerDefinition,
    EventManagerHealth,
    EventManagerSettings,
)
from madsci.event_manager.events_csv_exporter import CSVExporter
from madsci.event_manager.notifications import EmailAlerts
from madsci.event_manager.utilization_analyzer import UtilizationAnalyzer
from pymongo import MongoClient, errors
from pymongo.synchronous.database import Database


class EventManager(AbstractManagerBase[EventManagerSettings, EventManagerDefinition]):
    """Event Manager REST Server."""

    SETTINGS_CLASS = EventManagerSettings
    DEFINITION_CLASS = EventManagerDefinition

    def __init__(
        self,
        settings: Optional[EventManagerSettings] = None,
        definition: Optional[EventManagerDefinition] = None,
        db_connection: Optional[Database] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Event Manager."""
        # Store additional dependencies before calling super().__init__
        self._db_connection = db_connection
        super().__init__(settings=settings, definition=definition, **kwargs)

        # Initialize database connection and collections
        self._setup_database()

    def setup_logging(self) -> None:
        """Setup logging for the event manager. Prevent recursive logging."""
        self._logger = EventClient(
            name=f"{self._definition.name}", event_server_url=None
        )
        self._logger.event_server = None

    def _setup_database(self) -> None:
        """Setup database connection and collections."""
        if self._db_connection is None:
            db_client = MongoClient(self.settings.db_url)
            self._db_connection = db_client[self.settings.collection_name]

        self.events = self._db_connection["events"]

    def get_health(self) -> EventManagerHealth:
        """Get the health status of the Event Manager."""
        health = EventManagerHealth()

        try:
            # Test database connection
            self._db_connection.command("ping")
            health.db_connected = True

            # Get total event count
            health.total_events = self.events.count_documents({})

            health.healthy = True
            health.description = "Event Manager is running normally"

        except Exception as e:
            health.healthy = False
            health.db_connected = False
            health.description = f"Database connection failed: {e!s}"

        return health

    @post("/event")
    async def log_event(self, event: Event) -> Event:
        """Create a new event."""
        try:
            mongo_data = event.to_mongo()
            try:
                self.events.insert_one(mongo_data)
            except errors.DuplicateKeyError:
                self.logger.warning(
                    f"Duplicate event ID {event.event_id} - skipping insert"
                )
                # Just continue - don't fail the request
        except Exception as e:
            self.logger.error(f"Failed to log event: {e}")
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
            self.logger.error(f"Event with ID {event_id} not found")
            raise HTTPException(
                status_code=404, detail=f"Event with ID {event_id} not found"
            )
        return event

    @get("/events")
    async def get_events(
        self, number: int = 100, level: Union[int, EventLogLevel] = 0
    ) -> Dict[str, Event]:
        """Get the latest events"""
        event_list = (
            self.events.find({"log_level": {"$gte": int(level)}})
            .sort("event_timestamp", pymongo.DESCENDING)
            .limit(number)
            .to_list()
        )
        return {str(event["_id"]): Event.model_validate(event) for event in event_list}

    @post("/events/query")
    async def query_events(self, selector: Any = Body()) -> Dict[str, Event]:  # noqa: B008
        """Query events based on a selector. Note: this is a raw query, so be careful."""
        event_list = self.events.find(selector).to_list()
        return {event["_id"]: event for event in event_list}

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
            self.logger.error(f"Error generating session utilization: {e}")
            return {"error": f"Failed to generate report: {e!s}"}

    def _get_session_analyzer(self) -> Optional[UtilizationAnalyzer]:
        """Create session analyzer on-demand."""
        try:
            return UtilizationAnalyzer(self.events)
        except Exception as e:
            self.logger.error(f"Failed to create session analyzer: {e}")
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


# Main entry point for running the server
if __name__ == "__main__":
    manager = EventManager()
    manager.run_server()
