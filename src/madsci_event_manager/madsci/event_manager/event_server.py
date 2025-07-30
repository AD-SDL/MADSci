"""REST Server for the MADSci Event Manager"""

from pathlib import Path
from typing import Any, Optional, Union

import uvicorn
from fastapi import FastAPI, Query
from fastapi.params import Body
from fastapi.responses import Response

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
import datetime
from datetime import datetime, timedelta, timezone
import traceback
from madsci.common.ownership import global_ownership_info
from madsci.common.events_csv_exporter import CSVExporter

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
    
    @app.get("/utilization/sessions", response_model=None)
    async def get_session_utilization(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        csv_format: bool = Query(False, description="Return data in CSV format"),
        save_to_file: bool = Query(False, description="Save CSV to server filesystem"),
        output_path: Optional[str] = Query(None, description="Server path to save CSV files")
    ):
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
            # Parse time parameters
            parsed_start = None
            parsed_end = None
            
            if start_time:
                parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if end_time:
                parsed_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # Generate session-based report
            report = analyzer.generate_session_based_report(parsed_start, parsed_end)
            
            # Handle CSV export if requested
            if csv_format:
                try:
                    if save_to_file:
                        # Save to server filesystem
                        if not output_path:
                            return {"error": "output_path is required when save_to_file=True"}
                        
                        file_path = CSVExporter.export_utilization_report_to_csv(
                            report_data=report,
                            output_path=output_path
                        )
                        
                        return {
                            "message": "CSV file saved successfully",
                            "file_path": file_path,
                            "csv_format": True,
                            "saved_to_server": True,
                            "report_type": "session_utilization"
                        }
                    else:
                        # Return CSV for download
                        csv_content = CSVExporter.export_utilization_report_to_csv(
                            report_data=report,
                            output_path=None
                        )
                        
                        return Response(
                            content=csv_content,
                            media_type="text/csv",
                            headers={
                                "Content-Disposition": "attachment; filename=session_utilization_report.csv"
                            }
                        )
                except Exception as e:
                    logger.log_error(f"Error generating CSV: {e}")
                    return {"error": f"CSV generation failed: {str(e)}"}
            
            # Default JSON response
            return report
            
        except Exception as e:
            logger.log_error(f"Error generating session utilization: {e}")
            return {"error": f"Failed to generate report: {str(e)}"}


    @app.get("/utilization/periods", response_model=None)  
    async def get_utilization_periods(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        analysis_type: str = "daily",
        user_timezone: str = "America/Chicago",
        include_users: bool = True,
        csv_format: bool = Query(False, description="Return data in CSV format"),
        save_to_file: bool = Query(False, description="Save CSV to server filesystem"),
        output_path: Optional[str] = Query(None, description="Server path to save CSV files")
    ):
        """
        Get time-series utilization analysis with periodic breakdowns.
        
        PARAMETERS:
        - start_time: Optional ISO format start time (if not provided, uses database range)
        - end_time: Optional ISO format end time (if not provided, uses database range)
        - analysis_type: "hourly", "daily", "weekly", "monthly"
        - user_timezone: Timezone for period boundaries (e.g., "America/Chicago")
        - include_users: Whether to include user utilization data
        - csv_format: If True, returns CSV data instead of JSON
        - save_to_file: If True, saves CSV to server filesystem (requires output_path)
        - output_path: Server path where CSV files should be saved
        """
        
        analyzer = _get_session_analyzer()
        if analyzer is None:
            return {"error": "Failed to create session analyzer"}
        
        ts_analyzer = TimeSeriesAnalyzer(analyzer)
        
        try:
            # Parse time parameters (if provided)
            parsed_start = None
            parsed_end = None
            
            if start_time:
                parsed_start = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
            
            if end_time:
                parsed_end = datetime.fromisoformat(end_time.replace('Z', '+00:00')).astimezone(timezone.utc).replace(tzinfo=None)
            
            # Let the analyzer determine the actual analysis period based on available data
            utilization = ts_analyzer.generate_summary_report(
                parsed_start, parsed_end, analysis_type, user_timezone
            )
            
            # Add user utilization if requested
            if include_users:
                # Use the same time period that was actually analyzed
                actual_start = datetime.fromisoformat(utilization["summary_metadata"]["period_start"])
                actual_end = datetime.fromisoformat(utilization["summary_metadata"]["period_end"])
                
                user_report = analyzer.generate_user_utilization_report(actual_start, actual_end)
                
                if "error" not in user_report:
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
                        if key == "key_metrics":
                            enhanced_summary["user_utilization"] = user_summary
                    
                    utilization = enhanced_summary
                else:
                    utilization["user_utilization"] = {
                        "error": user_report.get("error", "Failed to generate user summary")
                    }
            
            # Handle CSV export if requested
            if csv_format:
                try:
                    if save_to_file:
                        if not output_path:
                            return {"error": "output_path is required when save_to_file=True"}
                        
                        result = CSVExporter.export_utilization_periods_to_csv(
                            report_data=utilization,
                            output_path=output_path
                        )
                        
                        if isinstance(result, dict):
                            return {
                                "message": "CSV files saved successfully",
                                "files_saved": result,
                                "csv_format": True,
                                "saved_to_server": True,
                                "report_type": "utilization_periods"
                            }
                        else:
                            return {
                                "message": "CSV file saved successfully",
                                "file_path": result,
                                "csv_format": True,
                                "saved_to_server": True,
                                "report_type": "utilization_periods"
                            }
                    else:
                        csv_content = CSVExporter.export_utilization_periods_to_csv(
                            report_data=utilization,
                            output_path=None
                        )
                        
                        return Response(
                            content=csv_content,
                            media_type="text/csv",
                            headers={
                                "Content-Disposition": f"attachment; filename=utilization_periods_{analysis_type}_report.csv"
                            }
                        )
                except Exception as e:
                    logger.log_error(f"Error generating CSV: {e}")
                    return {"error": f"CSV generation failed: {str(e)}"}
            
            return utilization
            
        except Exception as e:
            logger.log_error(f"Error generating utilization periods: {e}")
            return {"error": f"Failed to generate summary: {str(e)}"}

    @app.get("/utilization/users", response_model=None)
    async def get_user_utilization_report(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        csv_format: bool = Query(False, description="Return data in CSV format"),
        save_to_file: bool = Query(False, description="Save CSV to server filesystem"),
        output_path: Optional[str] = Query(None, description="Server path to save CSV files")
    ):
        """
        Generate detailed user utilization report based on workflow authors.
        
        NEW PARAMETERS:
        - csv_format: If True, returns CSV data instead of JSON
        - save_to_file: If True, saves CSV to server filesystem (requires output_path)
        - output_path: Server path where CSV files should be saved
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
            
            # Handle CSV export if requested
            if csv_format:
                try:
                    if save_to_file:
                        # Save to server filesystem
                        if not output_path:
                            return {"error": "output_path is required when save_to_file=True"}
                        
                        file_path = CSVExporter.export_user_utilization_to_csv(
                            report_data=report,
                            output_path=output_path,
                            detailed=True
                        )
                        
                        return {
                            "message": "CSV file saved successfully",
                            "file_path": file_path,
                            "csv_format": True,
                            "saved_to_server": True,
                            "report_type": "user_utilization"
                        }
                    else:
                        # Return CSV for download
                        csv_content = CSVExporter.export_user_utilization_to_csv(
                            report_data=report,
                            output_path=None,
                            detailed=True
                        )
                        
                        return Response(
                            content=csv_content,
                            media_type="text/csv",
                            headers={
                                "Content-Disposition": "attachment; filename=user_utilization_report.csv"
                            }
                        )
                except Exception as e:
                    logger.log_error(f"Error generating CSV: {e}")
                    return {"error": f"CSV generation failed: {str(e)}"}
            
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
