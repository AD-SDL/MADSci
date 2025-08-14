"""REST Server for the MADSci Event Manager"""

import datetime
from datetime import datetime  # noqa: F811
from pathlib import Path
from typing import Annotated, Any, Dict, Optional, Tuple, Union

import pymongo
import uvicorn
from fastapi import FastAPI, Query
from fastapi.exceptions import HTTPException
from fastapi.params import Body
from fastapi.responses import Response
from madsci.client.event_client import EventClient
from madsci.common.ownership import global_ownership_info
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.event_types import (
    Event,
    EventLogLevel,
    EventManagerDefinition,
    EventManagerSettings,
)
from madsci.event_manager.events_csv_exporter import CSVExporter
from madsci.event_manager.notifications import EmailAlerts
from madsci.event_manager.time_series_analyzer import TimeSeriesAnalyzer
from madsci.event_manager.utilization_analyzer import UtilizationAnalyzer
from pymongo import MongoClient, errors
from pymongo.synchronous.database import Database


def create_event_server(  # noqa: C901, PLR0915
    event_manager_definition: Optional[EventManagerDefinition] = None,
    event_manager_settings: Optional[EventManagerSettings] = None,
    db_connection: Optional[Database] = None,
    context: Optional[MadsciContext] = None,
) -> FastAPI:
    """Creates an Event Manager's REST server with optional utilization tracking."""

    logger = EventClient()
    logger.event_server = None  # * Ensure we don't recursively log events

    event_manager_settings = event_manager_settings or EventManagerSettings()
    logger.log_info(event_manager_settings)

    if event_manager_definition is None:
        def_path = Path(event_manager_settings.event_manager_definition).expanduser()
        if def_path.exists():
            event_manager_definition = EventManagerDefinition.from_yaml(
                def_path,
            )
        else:
            event_manager_definition = EventManagerDefinition()
        logger.log_info(f"Writing to event manager definition file: {def_path}")
        event_manager_definition.to_yaml(def_path)

    global_ownership_info.manager_id = event_manager_definition.event_manager_id
    logger = EventClient(name=f"event_manager.{event_manager_definition.name}")
    logger.event_server = None  # * Ensure we don't recursively log events
    logger.log_info(event_manager_definition)
    if db_connection is None:
        db_client = MongoClient(event_manager_settings.db_url)
        db_connection = db_client[event_manager_settings.collection_name]
    context = context or MadsciContext()
    logger.log_info(context)

    app = FastAPI()
    events = db_connection["events"]

    @app.get("/")
    @app.get("/info")
    @app.get("/definition")
    async def root() -> EventManagerDefinition:
        """Return the Event Manager Definition"""
        return event_manager_definition

    @app.post("/event")
    async def log_event(event: Event) -> Event:
        """Create a new event."""
        try:
            mongo_data = event.to_mongo()
            try:
                events.insert_one(mongo_data)
            except errors.DuplicateKeyError:
                logger.log_warning(
                    f"Duplicate event ID {event.event_id} - skipping insert"
                )
                # Just continue - don't fail the request
        except Exception as e:
            logger.log_error(f"Failed to log event: {e}")
            raise e

        if (
            event.alert or event.log_level >= event_manager_settings.alert_level
        ) and event_manager_settings.email_alerts:
            email_alerter = EmailAlerts(
                config=event_manager_settings.email_alerts,
                logger=logger,
            )
            email_alerter.send_email_alerts(event)
        return event

    @app.get("/event/{event_id}")
    async def get_event(event_id: str) -> Event:
        """Look up an event by event_id"""
        event = events.find_one({"_id": event_id})
        if not event:
            logger.log_error(f"Event with ID {event_id} not found")
            raise HTTPException(
                status_code=404, detail=f"Event with ID {event_id} not found"
            )
        return event

    @app.get("/events")
    async def get_events(
        number: int = 100, level: Union[int, EventLogLevel] = 0
    ) -> dict[str, Event]:
        """Get the latest events"""

        event_list = (
            events.find({"log_level": {"$gte": int(level)}})
            .sort("event_timestamp", pymongo.DESCENDING)
            .limit(number)
            .to_list()
        )
        return {str(event["_id"]): Event.model_validate(event) for event in event_list}

    @app.post("/events/query")
    async def query_events(selector: Any = Body()) -> dict[str, Event]:  # noqa: B008
        """Query events based on a selector. Note: this is a raw query, so be careful."""
        event_list = events.find(selector).to_list()
        return {event["_id"]: event for event in event_list}

    @app.get("/utilization/sessions", response_model=None)
    async def get_session_utilization(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        csv_format: Annotated[
            bool, Query(description="Return data in CSV format")
        ] = False,
        save_to_file: Annotated[
            bool, Query(description="Save CSV to server filesystem")
        ] = False,
        output_path: Annotated[
            Optional[str], Query(description="Server path to save CSV files")
        ] = None,
    ) -> Union[Dict[str, Any], Response]:
        """
        Generate comprehensive session-based utilization report.

        PARAMETERS:
        - csv_format: If True, returns CSV data instead of JSON
        - save_to_file: If True, saves CSV to server filesystem (requires output_path)
        - output_path: Server path where CSV files should be saved

        RESPONSE TYPES:
        - csv_format=False: JSON dict (default behavior)
        - csv_format=True, save_to_file=False: CSV download
        - csv_format=True, save_to_file=True: JSON with file path info
        """

        analyzer = _get_session_analyzer()
        if analyzer is None:
            return {"error": "Failed to create session analyzer"}

        try:
            # Parse time parameters and generate session-based report
            parsed_start, parsed_end = _parse_session_time_parameters(
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
            logger.log_error(f"Error generating session utilization: {e}")
            return {"error": f"Failed to generate report: {e!s}"}

    @app.get("/utilization/periods", response_model=None)
    async def get_utilization_periods(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        analysis_type: str = "daily",
        user_timezone: str = "America/Chicago",
        include_users: bool = True,
        csv_format: Annotated[
            bool, Query(description="Return data in CSV format")
        ] = False,
        save_to_file: Annotated[
            bool, Query(description="Save CSV to server filesystem")
        ] = False,
        output_path: Annotated[
            Optional[str], Query(description="Server path to save CSV files")
        ] = None,
    ) -> Union[Dict[str, Any], Response]:
        """Get time-series utilization analysis with periodic breakdowns."""

        # Setup analyzer
        analyzer = _get_session_analyzer()
        if analyzer is None:
            raise ValueError("Failed to create session analyzer")

        try:
            ts_analyzer = TimeSeriesAnalyzer(analyzer)

            # Generate utilization report
            utilization = ts_analyzer.generate_utilization_report_with_times(
                start_time, end_time, analysis_type, user_timezone
            )

            # Early return for errors
            if "error" in utilization:
                return utilization

            # Add user data if requested
            if include_users:
                utilization = ts_analyzer.add_user_utilization_to_report(utilization)

            # Handle CSV export if requested
            if csv_format:
                csv_result = CSVExporter.handle_api_csv_export(
                    utilization, save_to_file, output_path
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
            return utilization

        except Exception as e:
            logger.log_error(f"Error generating utilization periods: {e}")
            return {"error": f"Failed to generate summary: {e!s}"}

    @app.get("/utilization/users", response_model=None)
    async def get_user_utilization_report(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        csv_format: Annotated[
            bool, Query(description="Return data in CSV format")
        ] = False,
        save_to_file: Annotated[
            bool, Query(description="Save CSV to server filesystem")
        ] = False,
        output_path: Annotated[
            Optional[str], Query(description="Server path to save CSV files")
        ] = None,
    ) -> Union[Dict[str, Any], Response]:
        """
        Generate detailed user utilization report based on workflow authors.

        Parameters:
        - csv_format: If True, returns CSV data instead of JSON
        - save_to_file: If True, saves CSV to server filesystem (requires output_path)
        - output_path: Server path where CSV files should be saved
        """

        analyzer = _get_session_analyzer()
        if analyzer is None:
            return {"error": "Failed to create session analyzer"}

        try:
            ts_analyzer = TimeSeriesAnalyzer(analyzer)

            # Parse time parameters and generate report
            parsed_start, parsed_end = ts_analyzer.parse_time_parameters(
                start_time, end_time
            )
            report = analyzer.generate_user_utilization_report(parsed_start, parsed_end)

            # Handle CSV export if requested
            if csv_format:
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

            return report

        except Exception as e:
            logger.log_error(f"Error generating user utilization report: {e}")
            return {"error": f"Failed to generate user report: {e!s}"}

    def _get_session_analyzer() -> Optional[UtilizationAnalyzer]:
        """Create session analyzer on-demand."""
        try:
            return UtilizationAnalyzer(events)
        except Exception as e:
            logger.log_error(f"Failed to create session analyzer: {e}")
            return None

    def _parse_session_time_parameters(
        start_time: Optional[str], end_time: Optional[str]
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Parse time parameters for session utilization reports."""
        parsed_start = None
        parsed_end = None

        if start_time:
            parsed_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if end_time:
            parsed_end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))

        return parsed_start, parsed_end

    return app


if __name__ == "__main__":
    event_manager_settings = EventManagerSettings()
    app = create_event_server(
        event_manager_settings=event_manager_settings,
    )
    uvicorn.run(
        app,
        host=event_manager_settings.event_server_url.host,
        port=event_manager_settings.event_server_url.port,
    )
