"""REST Server for the MADSci Event Manager"""

from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.params import Body
from madsci.client.event_client import EventClient
from madsci.common.types.context_types import MadsciContext
from madsci.common.types.event_types import (
    Event,
    EventManagerDefinition,
    EventManagerSettings,
)
from madsci.event_manager.utilization_analyzer import UtilizationAnalyzer, UtilizationVisualizer
from madsci.event_manager.notifications import EmailAlerts
from pymongo import MongoClient
from pymongo.synchronous.database import Database
from contextlib import asynccontextmanager
import datetime
from datetime import timedelta

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
    from madsci.common.ownership import global_ownership_info

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
            # Test the conversion
            mongo_data = event.to_mongo()            
            # Test the insertion
            result = events.insert_one(mongo_data)
            
        except Exception as e:
            import traceback
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

    # Utilization analysis endpoints - create analyzer on-demand
    def get_utilization_analyzer():
        """Create utilization analyzer on-demand."""
        try:
            return UtilizationAnalyzer(events)
        except Exception as e:
            logger.log_error(f"Failed to create utilization analyzer: {e}")
            return None

    def get_utilization_visualizer():
        """Create utilization visualizer on-demand."""
        try:
            return UtilizationVisualizer(events)
        except Exception as e:
            logger.log_error(f"Failed to create utilization visualizer: {e}")
            return None


    @app.get("/utilization/summary")
    async def get_utilization_summary(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        hours_back: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Get utilization summary for a time range using container-compatible analyzer.
        
        Parameters:
        - start_time: ISO format start time (optional)
        - end_time: ISO format end time (optional) 
        - hours_back: Hours back from now (optional, for backwards compatibility)
        
        If no parameters provided, analyzes current system session.
        """
        print("GET /utilization/summary called")
        analyzer = get_utilization_analyzer()
        if analyzer is None:
            return {"error": "Failed to create utilization analyzer"}
        
        try:
            # Parse time parameters
            parsed_start = None
            parsed_end = None
            
            if hours_back and not start_time and not end_time:
                # Backwards compatibility mode
                parsed_end = datetime.datetime.now()
                parsed_start = parsed_end - timedelta(hours=hours_back)
                print(f"Using hours_back={hours_back}: {parsed_start} to {parsed_end}")
            else:
                if start_time:
                    parsed_start = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if end_time:
                    parsed_end = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                print(f"Using explicit times: {parsed_start} to {parsed_end}")
            
            # Analyze utilization using container-compatible analyzer
            print("Calling analyzer.analyze_utilization...")
            summary = analyzer.analyze_utilization(parsed_start, parsed_end)
            print("Analysis complete, returning summary")
            return summary.model_dump()
            
        except Exception as e:
            logger.log_error(f"Error analyzing utilization: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to analyze utilization: {str(e)}"}

    @app.get("/utilization/analysis")
    async def get_detailed_utilization_analysis(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        include_timeline: bool = False
    ) -> dict[str, Any]:
        """
        Get detailed utilization analysis with additional insights using container-compatible analyzer.
        
        Parameters:
        - start_time: ISO format start time (optional)
        - end_time: ISO format end time (optional)
        - include_timeline: Whether to include event timeline (optional)
        """
        print("GET /utilization/analysis called")
        analyzer = get_utilization_analyzer()
        if analyzer is None:
            return {"error": "Failed to create utilization analyzer"}
        
        try:
            # Parse time parameters
            parsed_start = None
            parsed_end = None
            
            if start_time:
                parsed_start = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if end_time:
                parsed_end = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            print(f"Analyzing detailed utilization: {parsed_start} to {parsed_end}")
            
            # Get basic analysis
            summary = analyzer.analyze_utilization(parsed_start, parsed_end)
            
            # Determine actual timeframe used
            analysis_start, analysis_end = analyzer._determine_timeframe(parsed_start, parsed_end)
            
            result = {
                "analysis_period": {
                    "start": analysis_start.isoformat(),
                    "end": analysis_end.isoformat(),
                    "duration_hours": (analysis_end - analysis_start).total_seconds() / 3600
                },
                "summary": summary.model_dump(),
                "insights": {
                    "peak_utilization_node": None,
                    "least_utilized_node": None,
                    "total_experiments": len(summary.system_utilization.active_experiments),
                    "total_workflows": len(summary.system_utilization.active_workflows),
                    "nodes_analyzed": len(summary.node_utilizations)
                }
            }
            
            # Find peak and least utilized nodes
            if summary.node_utilizations:
                sorted_nodes = sorted(
                    summary.node_utilizations.items(), 
                    key=lambda x: x[1].utilization_percentage, 
                    reverse=True
                )
                result["insights"]["peak_utilization_node"] = {
                    "node_id": sorted_nodes[0][0],
                    "utilization": sorted_nodes[0][1].utilization_percentage
                }
                result["insights"]["least_utilized_node"] = {
                    "node_id": sorted_nodes[-1][0],
                    "utilization": sorted_nodes[-1][1].utilization_percentage
                }
            
            # Include event timeline if requested
            if include_timeline:
                print("Including timeline in analysis...")
                # Get recent events for timeline
                timeline_events = list(events.find(
                    {"event_timestamp": {"$gte": analysis_start, "$lte": analysis_end}}
                ).sort("event_timestamp", -1).limit(50))
                
                result["timeline"] = [
                    {
                        "timestamp": event["event_timestamp"].isoformat() if hasattr(event["event_timestamp"], 'isoformat') else str(event["event_timestamp"]),
                        "event_type": event["event_type"],
                        "node_id": analyzer._extract_node_id(event),
                        "experiment_id": analyzer._extract_experiment_id(event),
                        "workflow_id": analyzer._extract_workflow_id(event)
                    }
                    for event in timeline_events
                ]
            
            print("Detailed analysis complete")
            return result
            
        except Exception as e:
            logger.log_error(f"Error in detailed utilization analysis: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to analyze utilization: {str(e)}"}

    @app.get("/utilization/graphs/system")
    async def get_system_utilization_graph(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        hours_back: Optional[int] = None
    ) -> dict[str, Any]:
        """Generate system utilization graph with container-compatible visualizer."""
        print("GET /utilization/graphs/system called")
        visualizer = get_utilization_visualizer()
        if visualizer is None:
            return {"error": "Failed to create utilization visualizer"}
        
        try:
            # Parse time parameters
            parsed_start = None
            parsed_end = None
            
            if hours_back and not start_time and not end_time:
                parsed_end = datetime.datetime.now()
                parsed_start = parsed_end - timedelta(hours=hours_back)
            else:
                if start_time:
                    parsed_start = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if end_time:
                    parsed_end = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            print(f"Generating system graph for: {parsed_start} to {parsed_end}")
            
            graph_base64 = visualizer.generate_system_utilization_graph(
                parsed_start, parsed_end, hours_back
            )
            
            return {
                "graph": graph_base64,
                "format": "png_base64",
                "analysis_start": parsed_start.isoformat() if parsed_start else None,
                "analysis_end": parsed_end.isoformat() if parsed_end else None,
                "generated_at": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            logger.log_error(f"Error generating system utilization graph: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to generate graph: {str(e)}"}

    @app.get("/utilization/graphs/node/{node_id}")
    async def get_node_utilization_graph(
        node_id: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        hours_back: Optional[int] = None
    ) -> dict[str, Any]:
        """Generate node utilization graph with container-compatible visualizer."""
        print(f"GET /utilization/graphs/node/{node_id} called")
        visualizer = get_utilization_visualizer()
        if visualizer is None:
            return {"error": "Failed to create utilization visualizer"}
        
        try:
            # Parse time parameters
            parsed_start = None
            parsed_end = None
            
            if hours_back and not start_time and not end_time:
                parsed_end = datetime.datetime.now()
                parsed_start = parsed_end - timedelta(hours=hours_back)
            else:
                if start_time:
                    parsed_start = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if end_time:
                    parsed_end = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            print(f"Generating node graph for {node_id}: {parsed_start} to {parsed_end}")
            
            graph_base64 = visualizer.generate_node_utilization_graph(
                node_id, parsed_start, parsed_end, hours_back
            )
            
            return {
                "graph": graph_base64,
                "format": "png_base64",
                "node_id": node_id,
                "analysis_start": parsed_start.isoformat() if parsed_start else None,
                "analysis_end": parsed_end.isoformat() if parsed_end else None,
                "generated_at": datetime.datetime.now().isoformat()
            }
        except Exception as e:
            logger.log_error(f"Error generating node utilization graph for {node_id}: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to generate graph: {str(e)}"}

    @app.get("/utilization/report")
    async def get_comprehensive_utilization_report(
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        hours_back: Optional[int] = None,
        include_graphs: bool = True
    ) -> dict[str, Any]:
        """Generate comprehensive utilization report using container-compatible analyzer."""
        print("GET /utilization/report called")
        analyzer = get_utilization_analyzer()
        if analyzer is None:
            return {"error": "Failed to create utilization analyzer"}
        
        try:
            # Parse time parameters
            parsed_start = None
            parsed_end = None
            
            if hours_back and not start_time and not end_time:
                parsed_end = datetime.datetime.now()
                parsed_start = parsed_end - timedelta(hours=hours_back)
            else:
                if start_time:
                    parsed_start = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                if end_time:
                    parsed_end = datetime.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            print(f"Generating comprehensive report: {parsed_start} to {parsed_end}")
            
            # Get analysis
            summary = analyzer.analyze_utilization(parsed_start, parsed_end)
            analysis_start, analysis_end = analyzer._determine_timeframe(parsed_start, parsed_end)
            
            # Build report
            report = {
                "analysis_period": {
                    "start": analysis_start.isoformat(),
                    "end": analysis_end.isoformat(),
                    "duration_hours": (analysis_end - analysis_start).total_seconds() / 3600
                },
                "system_statistics": {
                    "utilization_percentage": summary.system_utilization.utilization_percentage,
                    "active_time_hours": summary.system_utilization.active_time / 3600,
                    "idle_time_hours": summary.system_utilization.idle_time / 3600,
                    "total_experiments": len(summary.system_utilization.active_experiments),
                    "total_workflows": len(summary.system_utilization.active_workflows)
                },
                "node_statistics": {},
                "summary": {
                    "nodes_analyzed": len(summary.node_utilizations),
                    "average_node_utilization": 0.0,
                    "peak_node_utilization": 0.0,
                    "generated_at": datetime.datetime.now().isoformat()
                }
            }
            
            # Calculate node statistics
            if summary.node_utilizations:
                utilizations = [node.utilization_percentage for node in summary.node_utilizations.values()]
                report["summary"]["average_node_utilization"] = sum(utilizations) / len(utilizations)
                report["summary"]["peak_node_utilization"] = max(utilizations)
                
                for node_id, node_util in summary.node_utilizations.items():
                    report["node_statistics"][node_id] = {
                        "utilization_percentage": node_util.utilization_percentage,
                        "busy_time_hours": node_util.busy_time / 3600,
                        "active_time_hours": getattr(node_util, 'active_time', 0) / 3600,
                        "current_state": node_util.current_state
                    }
            
            # Include graphs if requested
            if include_graphs:
                print("Adding graphs to report...")
                visualizer = get_utilization_visualizer()
                if visualizer:
                    try:
                        report["graphs"] = {
                            "system_utilization": visualizer.generate_system_utilization_graph(
                                parsed_start, parsed_end, hours_back
                            )
                        }
                        
                        # Generate node graphs for top 3 most utilized nodes
                        if summary.node_utilizations:
                            top_nodes = sorted(
                                summary.node_utilizations.items(),
                                key=lambda x: x[1].utilization_percentage,
                                reverse=True
                            )[:3]
                            
                            report["graphs"]["top_nodes"] = {}
                            for node_id, _ in top_nodes:
                                report["graphs"]["top_nodes"][node_id] = visualizer.generate_node_utilization_graph(
                                    node_id, parsed_start, parsed_end, hours_back
                                )
                    except Exception as e:
                        logger.log_warning(f"Failed to generate graphs for report: {e}")
                        report["graphs"] = {"error": "Graph generation failed"}
            
            print("Comprehensive report complete")
            return report
            
        except Exception as e:
            logger.log_error(f"Error generating utilization report: {e}")
            import traceback
            traceback.print_exc()
            return {"error": f"Failed to generate report: {str(e)}"}

    # Debug endpoint to show what events are available

    @app.get("/utilization/debug/events")
    async def debug_events(limit: int = 50) -> dict[str, Any]:
        """FIXED debug endpoint to show what events are available in the database."""
        try:
            # Use the events collection directly (same as the fixed analyzer)
            recent_events = list(events.find({}).sort("event_timestamp", -1).limit(limit))
            
            print(f"FIXED DEBUG: Found {len(recent_events)} events in collection")
            
            # Analyze event types
            event_type_counts = {}
            events_with_nodes = 0
            events_with_experiments = 0
            
            for event in recent_events:
                event_type = event.get("event_type", "unknown")
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
                
                # Check for node info (FIXED to handle your actual data structure)
                source = event.get("source", {})
                event_data = event.get("event_data", {})
                
                has_node = False
                if isinstance(source, dict):
                    # Check for node indicators in source
                    node_id = (source.get("node_id") or 
                            source.get("workcell_id") or 
                            source.get("manager_id"))
                    if node_id and any(indicator in str(node_id).lower() for indicator in 
                                    ["liquidhandler", "robotarm", "platereader", "node"]):
                        has_node = True
                
                if not has_node and isinstance(event_data, dict):
                    has_node = bool(event_data.get("node_id"))
                
                if has_node:
                    events_with_nodes += 1
                
                # Check for experiment info
                has_experiment = False
                if isinstance(source, dict):
                    has_experiment = bool(source.get("experiment_id"))
                if not has_experiment and isinstance(event_data, dict):
                    has_experiment = bool(event_data.get("experiment_id"))
                
                if has_experiment:
                    events_with_experiments += 1
            
            return {
                "total_events": len(recent_events),
                "events_with_nodes": events_with_nodes,
                "events_with_experiments": events_with_experiments,
                "event_type_counts": event_type_counts,
                "sample_events": [
                    {
                        "timestamp": str(event.get("event_timestamp", "unknown")),
                        "event_type": event.get("event_type", "unknown"),
                        "has_node_info": bool(
                            # FIXED node detection logic
                            (event.get("source", {}).get("node_id") or 
                            event.get("source", {}).get("workcell_id") or
                            event.get("event_data", {}).get("node_id")) and
                            any(indicator in str(event.get("source", {}).get("workcell_id", "")).lower() 
                                for indicator in ["liquidhandler", "robotarm", "platereader", "node"])
                        ),
                        "has_experiment_info": bool(
                            (event.get("source", {}).get("experiment_id") or
                            event.get("event_data", {}).get("experiment_id"))
                        ),
                        "source_info": {
                            "workcell_id": event.get("source", {}).get("workcell_id"),
                            "node_id": event.get("source", {}).get("node_id"),
                            "experiment_id": event.get("source", {}).get("experiment_id"),
                            "manager_id": event.get("source", {}).get("manager_id")
                        }
                    }
                    for event in recent_events[:10]
                ],
                "fix_status": "FIXED - Using corrected collection access and field mapping"
            }
        except Exception as e:
            return {
                "error": f"FIXED debug endpoint failed: {str(e)}",
                "fix_status": "ERROR in fixed implementation"
            }

    # Legacy endpoint for backwards compatibility
    @app.post("/events/query/utilization")
    async def query_utilization_events(
        hours_back: int = 24,
        utilization_type: Optional[str] = None
    ) -> dict[str, Any]:
        """Legacy endpoint - redirects to new analysis."""
        return await get_utilization_summary(hours_back=hours_back)

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
