"""REST Server for the MADSci Event Manager"""

from typing import Any, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.params import Body
from fastapi.routing import APIRouter
from madsci.client.event_client import EventClient
from madsci.common.types.event_types import Event, EventManagerDefinition
from pymongo import MongoClient
from pymongo.synchronous.collection import Collection
from pymongo.synchronous.database import Database


class EventServer:
    """A REST server for managing MADSci events across a lab."""

    event_manager_definition: Optional[EventManagerDefinition] = None
    db_client: MongoClient
    app = FastAPI()
    logger = EventClient()
    events: Collection

    def __init__(
        self,
        event_manager_definition: Optional[EventManagerDefinition] = None,
        db_connection: Optional[Database] = None,
    ) -> None:
        """Initialize the Event Manager Server."""
        if event_manager_definition is not None:
            self.event_manager_definition = event_manager_definition
        else:
            self.event_manager_definition = EventManagerDefinition.load_model(
                require_unique=True
            )
        if self.event_manager_definition is None:
            raise ValueError(
                "No event manager definition found, please specify a path with --definition, or add it to your lab definition's 'managers' section"
            )

        # * Logger
        event_manager_definition.event_client_config.event_server_url = (
            None  # * Remove event_server_url to prevent infinite loop
        )
        self.logger = EventClient(event_manager_definition.event_client_config)
        self.logger.log_info(self.event_manager_definition)

        # * DB Config
        if db_connection is not None:
            self.events_db = db_connection
        else:
            self.db_client = MongoClient(self.event_manager_definition.db_url)
            self.events_db = self.db_client["madsci_events"]
        self.events = self.events_db["events"]
        self.events.create_index("event_id", unique=True, background=True)

        # * REST Server Config
        self._configure_routes()

    async def root(self) -> EventManagerDefinition:
        """Return the Event Manager Definition"""
        return self.event_manager_definition

    async def create_event(self, event: Event) -> Event:
        """Create a new event."""
        self.events.insert_one(event.model_dump(mode="json"))
        return event

    async def get_event(self, event_id: str) -> Event:
        """Look up an event by event_id"""
        return self.events.find_one({"event_id": event_id})

    async def get_events(self, number: int = 100, level: int = 0) -> dict[str, Event]:
        """Get the latest events"""
        event_list = (
            self.events.find({"log_level": {"$gte": level}})
            .sort("event_timestamp", -1)
            .limit(number)
            .to_list()
        )
        return {event["event_id"]: event for event in event_list}

    async def query_events(self, selector: Any = Body()) -> dict[str, Event]:  # noqa: B008
        """Query events based on a selector. Note: this is a raw query, so be careful."""
        event_list = self.events.find(selector).to_list()
        return {event["event_id"]: event for event in event_list}

    def start_server(self) -> None:
        """Start the server."""
        uvicorn.run(
            self.app,
            host=self.event_manager_definition.host,
            port=self.event_manager_definition.port,
        )

    def _configure_routes(self) -> None:
        self.router = APIRouter()
        self.router.add_api_route("/", self.root, methods=["GET"])
        self.router.add_api_route("/event/{event_id}", self.get_event, methods=["GET"])
        self.router.add_api_route("/event", self.get_events, methods=["GET"])
        self.router.add_api_route("/events", self.get_events, methods=["GET"])
        self.router.add_api_route("/event", self.create_event, methods=["POST"])
        self.router.add_api_route("/events/query", self.query_events, methods=["POST"])
        self.router.add_api_route("/event/query", self.query_events, methods=["POST"])
        self.app.include_router(self.router)


if __name__ == "__main__":
    server = EventServer()
    server.start_server()
