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
from madsci.event_manager.utilization_tracker import UtilizationTracker
from madsci.event_manager.notifications import EmailAlerts
from pymongo import MongoClient
from pymongo.synchronous.database import Database
from contextlib import asynccontextmanager
import datetime

def create_event_server(  # noqa: C901
    event_manager_definition: Optional[EventManagerDefinition] = None,
    event_manager_settings: Optional[EventManagerSettings] = None,
    db_connection: Optional[Database] = None,
    context: Optional[MadsciContext] = None,
    enable_utilization_tracking: bool = True,
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
    # Initialize utilization tracking if enabled
    utilization_tracker = None
    utilization_visualizer = None
    
    if enable_utilization_tracking:
        try:
            utilization_tracker = UtilizationTracker(event_client=logger)
            utilization_tracker.start()
            utilization_visualizer = utilization_tracker.create_visualizer(db_connection)
            logger.log_info("Utilization tracking and visualization enabled")
        except Exception as e:
            logger.log_error(f"Failed to start utilization tracking: {e}")
            utilization_tracker = None
            utilization_visualizer = None

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
        events.insert_one(event.to_mongo())

        # Process event for utilization tracking
        if utilization_tracker:
            try:
                utilization_tracker.process_event(event)
            except Exception as e:
                logger.log_error(f"Error processing event for utilization tracking: {e}")

        if event.alert or event.log_level >= event_manager_settings.alert_level:  # noqa: SIM102
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

    # Utilization tracking endpoints
    @app.get("/utilization/summary")
    async def get_utilization_summary() -> dict[str, Any]:
        """Get current utilization summary."""
        if utilization_tracker:
            summary = utilization_tracker.get_utilization_summary()
            return summary.model_dump()
        else:
            return {"error": "Utilization tracking not enabled"}

    @app.post("/events/query/utilization")
    async def query_utilization_events(
        hours_back: int = 24,
        utilization_type: Optional[str] = None
    ) -> dict[str, Any]:
        """Query utilization events from the past N hours."""
        from datetime import timedelta
        
        since_time = datetime.now() - timedelta(hours=hours_back)
        
        selector = {
            "event_timestamp": {"$gte": since_time},
            "event_type": {"$in": ["utilization_system_summary", "utilization_node_summary"]}
        }
        
        if utilization_type:
            selector["event_data.utilization_type"] = utilization_type
        
        event_list = events.find(selector).sort("event_timestamp", 1).to_list()
        return {event["_id"]: event for event in event_list}

    # Graph generation endpoints
    @app.get("/utilization/graphs/system")
    async def get_system_utilization_graph(hours_back: int = 24) -> dict[str, Any]:
        """Generate system utilization graph."""
        if not utilization_visualizer:
            return {"error": "Utilization visualization not enabled"}
        
        try:
            graph_base64 = utilization_visualizer.generate_system_utilization_graph(hours_back)
            return {
                "graph": graph_base64,
                "format": "png_base64",
                "hours_analyzed": hours_back,
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.log_error(f"Error generating system utilization graph: {e}")
            return {"error": f"Failed to generate graph: {str(e)}"}

    @app.get("/utilization/graphs/node/{node_id}")
    async def get_node_utilization_graph(node_id: str, hours_back: int = 24) -> dict[str, Any]:
        """Generate node utilization graph."""
        if not utilization_visualizer:
            return {"error": "Utilization visualization not enabled"}
        
        try:
            graph_base64 = utilization_visualizer.generate_node_utilization_graph(node_id, hours_back)
            return {
                "graph": graph_base64,
                "format": "png_base64",
                "node_id": node_id,
                "hours_analyzed": hours_back,
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.log_error(f"Error generating node utilization graph for {node_id}: {e}")
            return {"error": f"Failed to generate graph: {str(e)}"}

    @app.get("/utilization/graphs/comparison")
    async def get_multi_node_comparison_graph(hours_back: int = 24, max_nodes: int = 6) -> dict[str, Any]:
        """Generate multi-node comparison graph."""
        if not utilization_visualizer:
            return {"error": "Utilization visualization not enabled"}
        
        try:
            graph_base64 = utilization_visualizer.generate_multi_node_comparison_graph(hours_back, max_nodes)
            return {
                "graph": graph_base64,
                "format": "png_base64",
                "hours_analyzed": hours_back,
                "max_nodes": max_nodes,
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.log_error(f"Error generating node comparison graph: {e}")
            return {"error": f"Failed to generate graph: {str(e)}"}

    @app.get("/utilization/graphs/heatmap")
    async def get_utilization_heatmap(hours_back: int = 24) -> dict[str, Any]:
        """Generate utilization heatmap."""
        if not utilization_visualizer:
            return {"error": "Utilization visualization not enabled"}
        
        try:
            graph_base64 = utilization_visualizer.generate_utilization_heatmap(hours_back)
            return {
                "graph": graph_base64,
                "format": "png_base64",
                "hours_analyzed": hours_back,
                "generated_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.log_error(f"Error generating utilization heatmap: {e}")
            return {"error": f"Failed to generate graph: {str(e)}"}

    @app.get("/utilization/report")
    async def get_utilization_report(hours_back: int = 24) -> dict[str, Any]:
        """Generate comprehensive utilization report with statistics and graphs."""
        if not utilization_visualizer:
            return {"error": "Utilization visualization not enabled"}
        
        try:
            report = utilization_visualizer.generate_utilization_report(hours_back)
            return report
        except Exception as e:
            logger.log_error(f"Error generating utilization report: {e}")
            return {"error": f"Failed to generate report: {str(e)}"}

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
