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
    
    @app.get("/utilization/sessions")
    async def get_session_utilization(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Generate comprehensive session-based utilization report.
        
        Sessions represent workcell/lab start and stop periods. Each session
        indicates when laboratory equipment was actively configured and available.
        
        Parameters:
        - start_time: Optional ISO format start time (e.g., "2025-07-21T10:00:00Z")  
        - end_time: Optional ISO format end time (e.g., "2025-07-21T18:00:00Z")
        - If no times provided, analyzes ALL records in the database
        
        Returns:
        - JSON report with session details, overall summary, and metadata
        """
        
        analyzer = _get_session_analyzer()
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
            
            # Generate session-based report
            report = analyzer.generate_session_based_report(parsed_start, parsed_end)
            return report
            
        except Exception as e:
            logger.log_error(f"Error generating session utilization: {e}")
            return {"error": f"Failed to generate report: {str(e)}"}

    @app.get("/utilization/periods")
    async def get_utilization_periods(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        analysis_type: str = "daily",
        user_timezone: str = "America/Chicago",
        include_users: bool = True
    ) -> dict[str, Any]:
        """
        Get time-series utilization analysis with periodic breakdowns.
        
        Analyzes system utilization over time periods with proper session attribution.
        Optionally includes user utilization data for comprehensive analysis.
        
        Parameters:
        - start_time: Optional ISO format start time
        - end_time: Optional ISO format end time  
        - analysis_type: Time bucket type ("hourly", "daily", "weekly", "monthly")
        - user_timezone: Timezone for day/week boundaries (e.g., "America/Chicago")
        - include_users: Whether to include user utilization data
        
        Returns:
        - JSON report with time-series data, summaries, trends, and optional user data
        """
        
        analyzer = _get_session_analyzer()
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
            
            # Generate system utilization periods
            utilization = ts_analyzer.generate_summary_report(
                start_dt, end_dt, analysis_type, user_timezone
            )
            
            # Add user utilization if requested
            if include_users:
                user_report = analyzer.generate_user_utilization_report(start_dt, end_dt)
                
                if "error" not in user_report:
                    # Extract user summary from full report
                    user_utilization = user_report.get("user_utilization", {})
                    system_summary = user_report.get("system_summary", {})
                    
                    # Sort users by total runtime (most active first)
                    sorted_users = sorted(
                        user_utilization.values(), 
                        key=lambda x: x.get("total_runtime_hours", 0), 
                        reverse=True
                    )
                    
                    # Create compact user summaries (top 10 users)
                    top_users = []
                    for user in sorted_users[:10]:
                        top_users.append({
                            "author": user.get("author"),
                            "total_workflows": user.get("total_workflows"),
                            "total_runtime_hours": user.get("total_runtime_hours"),
                            "completion_rate_percent": user.get("completion_rate_percent"),
                            "average_workflow_duration_hours": user.get("average_workflow_duration_hours")
                        })
                    
                    user_summary = {
                        "total_users": len(user_utilization),
                        "author_attribution_rate_percent": system_summary.get("author_attribution_rate_percent", 0),
                        "top_users": top_users,
                        "system_totals": {
                            "total_workflows": system_summary.get("total_workflows", 0),
                            "total_runtime_hours": system_summary.get("total_runtime_hours", 0),
                            "completion_rate_percent": system_summary.get("completion_rate_percent", 0)
                        }
                    }
                    
                    # Insert user utilization after key_metrics
                    enhanced_summary = {}
                    for key, value in utilization.items():
                        enhanced_summary[key] = value
                        # Add user utilization after key_metrics
                        if key == "key_metrics":
                            enhanced_summary["user_utilization"] = user_summary
                    
                    return enhanced_summary
                else:
                    # If user summary failed, just add error info
                    utilization["user_utilization"] = {
                        "error": user_report.get("error", "Failed to generate user summary")
                    }
            
            return utilization
            
        except Exception as e:
            logger.log_error(f"Error generating utilization periods: {e}")
            return {"error": f"Failed to generate summary: {str(e)}"}
        
    @app.get("/utilization/users")
    async def get_user_utilization_report(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Generate detailed user utilization report based on workflow authors.
        
        Analyzes workflow patterns by user/author including completion rates,
        runtime statistics, and individual workflow details.
        
        Parameters:
        - start_time: Optional ISO format start time (e.g., "2025-07-21T10:00:00Z")
        - end_time: Optional ISO format end time (e.g., "2025-07-23T18:00:00Z")
        - If no times provided, analyzes ALL records in the database
        
        Returns:
        - JSON report with detailed user utilization data including:
          * Per-user workflow counts, completion rates, runtime hours
          * System-wide author attribution statistics  
          * Individual workflow details per user
        """
        
        analyzer = _get_session_analyzer()
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
            
            # Generate user utilization report
            report = analyzer.generate_user_utilization_report(parsed_start, parsed_end)
            return report
            
        except Exception as e:
            logger.log_error(f"Error generating user utilization report: {e}")
            return {"error": f"Failed to generate user report: {str(e)}"}
        
    def _get_session_analyzer():
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
