"""REST Server for the MADSci Event Manager"""

from pathlib import Path
from typing import Any, Optional, Union

import uvicorn
from fastapi import FastAPI
from fastapi.params import Body
from fastapi.responses import StreamingResponse
import io

from madsci.client.event_client import EventClient
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.event_types import (
    Event,
    EventManagerDefinition,
    EventManagerSettings,
)
from madsci.event_manager.utilization_analyzer import UtilizationAnalyzer
from madsci.event_manager.time_series_analyzer import TimeSeriesAnalyzer
from madsci.event_manager.notifications import EmailAlerts
from pymongo import MongoClient, errors
from pymongo.synchronous.database import Database
from contextlib import asynccontextmanager
import datetime
from datetime import datetime, timedelta, timezone
import traceback
from madsci.common.ownership import global_ownership_info

def create_event_server(  # noqa: C901
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
                result = events.insert_one(mongo_data)
            except errors.DuplicateKeyError as e:
                logger.log_warning(f"Duplicate event ID {event.event_id} - skipping insert")
                # Just continue - don't fail the request
                pass            
        except Exception as e:
            traceback.print_exc()
            raise e  
        
        if event.alert or event.log_level >= event_manager_settings.alert_level:
            if event_manager_settings.email_alerts:
                email_alerter = EmailAlerts(
                    config=event_manager_settings.email_alerts,
                    logger=logger,
                )
                email_alerter.send_email_alerts(event)
        return event
    
    @app.get("/event/{event_id}")
    async def get_event(event_id: str) -> Event:
        """Look up an event by event_id"""
        return events.find_one({"_id": event_id})

    @app.get("/events")
    async def get_events(number: int = 100, level: int = 0) -> dict[str, Event]:
        """Get the latest events"""
        if isinstance(level, str):
            # Try to convert EventLogLevel string to integer
            if "EventLogLevel." in level:
                level_name = level.split(".")[-1]
                level_map = {
                    "DEBUG": 10,
                    "INFO": 20,
                    "WARNING": 30,
                    "ERROR": 40,
                    "CRITICAL": 50
                }
                level = level_map.get(level_name, 0)
            else:
                try:
                    level = int(level)
                except ValueError:
                    level = 0
        
        event_list = (
            events.find({"log_level": {"$gte": level}})
            .sort("event_timestamp", -1)
            .limit(number)
            .to_list()
        )
        return {event["_id"]: event for event in event_list}

    @app.post("/events/query")
    async def query_events(selector: Any = Body()) -> dict[str, Event]:  # noqa: B008
        """Query events based on a selector. Note: this is a raw query, so be careful."""
        event_list = events.find(selector).to_list()
        return {event["_id"]: event for event in event_list}
    
    @app.get("/utilization/report")
    async def get_utilization_report(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Generate comprehensive session-based utilization report.
        
        Parameters:
        - start_time: Optional ISO format start time (e.g., "2025-07-21T10:00:00Z")  
        - end_time: Optional ISO format end time (e.g., "2025-07-21T18:00:00Z")
        - If no times provided, analyzes ALL records in the database
        
        Returns:
        - JSON report with session and utilization data
        """
        
        analyzer = get_session_analyzer()
        if analyzer is None:
            return {"error": "Failed to create session analyzer"}
        
        try:
            # Parse time parameters
            parsed_start = None
            parsed_end = None
            
            if start_time:
                parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if end_time:
                parsed_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # Let the analyzer handle all the logic (including full DB analysis)
            report = analyzer.generate_session_report(parsed_start, parsed_end)
            return report
            
        except Exception as e:
            logger.log_error(f"Error generating report: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to generate report: {str(e)}"}
        
    @app.get("/utilization/time_series")
    async def get_time_series_analysis(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        analysis_type: str = "daily",
        user_timezone: str = "America/Chicago"
    ) -> dict[str, Any]:
        """Generate time-series utilization analysis with timezone support."""
        
        print("GET /utilization/time_series called")
        analyzer = get_session_analyzer()
        if analyzer is None:
            return {"error": "Failed to create session analyzer"}
        
        ts_analyzer = TimeSeriesAnalyzer(analyzer)
        
        try:
            # Parse time parameters
            parsed_start = None
            parsed_end = None
            
            if start_time:
                parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
            if end_time:
                parsed_end = datetime.fromisoformat(end_time.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
            
            # FIXED: Don't override analysis_type with bucket_hours for monthly
            if analysis_type in ["monthly", "mounthly"]:
                # Use the analysis type directly, let the analyzer handle bucketing
                report = ts_analyzer.generate_time_series_report(
                    parsed_start or (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)),
                    parsed_end or datetime.now(timezone.utc).replace(tzinfo=None),
                    None,  # Let analyzer determine bucket size
                    analysis_type,
                    user_timezone
                )
            else:
                # Set bucket size based on analysis type
                bucket_hours = {
                    "hourly": 1,
                    "daily": 24,
                    "weekly": 168
                }.get(analysis_type, 24)
                
                # Generate report with timezone support
                report = ts_analyzer.generate_time_series_report(
                    parsed_start or (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)),
                    parsed_end or datetime.now(timezone.utc).replace(tzinfo=None),
                    bucket_hours,
                    analysis_type,
                    user_timezone
                )
            
            return report
            
        except Exception as e:
            print(f"Error generating time-series report: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to generate report: {str(e)}"}

    @app.get("/utilization/summary")
    async def get_utilization_summary(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        analysis_type: str = "daily",
        user_timezone: str = "America/Chicago"
    ) -> dict[str, Any]:
        """Get utilization summary using simplified analyzer."""
        
        print("GET /utilization/summary called")
        
        analyzer = get_session_analyzer()
        if analyzer is None:
            return {"error": "Failed to create session analyzer"}
        
        ts_analyzer = TimeSeriesAnalyzer(analyzer)
        
        try:
            # Parse times correctly
            if not end_time:
                end_dt = datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
            
            if not start_time:
                start_dt = end_dt - timedelta(days=7)  # Default to 7 days ago
            else:
                start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
            
            # Use the new method name
            summary = ts_analyzer.generate_summary_report(
                start_dt, end_dt, analysis_type, user_timezone
            )
            
            return summary
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to generate summary: {str(e)}"}
    
    def get_session_analyzer():
        """Create session analyzer on-demand."""
        try:
            return UtilizationAnalyzer(events)
        except Exception as e:
            logger.log_error(f"Failed to create session analyzer: {e}")
            return None
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
