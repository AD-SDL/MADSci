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
from madsci.event_manager.notifications import EmailAlerts
from pymongo import MongoClient
from pymongo.synchronous.database import Database


def create_event_server(  # noqa: C901
    event_manager_definition: Optional[EventManagerDefinition] = None,
    event_manager_settings: Optional[EventManagerSettings] = None,
    db_connection: Optional[Database] = None,
    context: Optional[MadsciContext] = None,
) -> FastAPI:
    """Creates an Event Manager's REST server."""

    logger = EventClient()

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
    logger = EventClient(name=f"event_manager.{event_manager_definition.name}")
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
        events.insert_one(event.to_mongo())
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
