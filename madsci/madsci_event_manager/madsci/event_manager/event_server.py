"""REST Server for the MADSci Event Manager"""

from collections import OrderedDict

import uvicorn
from fastapi import FastAPI

from madsci.client.event_client import EventClient
from madsci.common.definition_loaders import (
    manager_definition_loader,
)
from madsci.common.types.event_types import Event
from madsci.common.types.squid_types import ManagerType

app = FastAPI()

events = OrderedDict()
logger = EventClient(name=__name__)


@app.get("/event/{event_id}")
async def get_event(event_id: str) -> Event:
    """Look up an event by event_id"""
    return events[event_id]


@app.get("/event")
@app.get("/events")
async def get_events(number: int = 100, level: int = 0) -> dict[str, Event]:
    """Get the latest events"""
    selected_events = OrderedDict()
    for event in reversed(list(events.values())):
        if event.log_level > level:
            selected_events[event.event_id] = event
        if len(selected_events) >= number:
            break
    return selected_events


@app.post("/event")
async def create_event(event: Event) -> Event:
    """Create a new event."""
    if not events.get(event.event_id):
        events[event.event_id] = event
    return event


if __name__ == "__main__":
    manager_definitions = manager_definition_loader()
    event_manager_definition = None
    for manager in manager_definitions:
        if manager.manager_type == ManagerType.EVENT_MANAGER:
            event_manager_definition = manager
    if event_manager_definition is None:
        raise ValueError(
            "No event manager definition found, please specify a path with --definition, or add it to your lab definition's 'managers' section"
        )
    logger.log_info(event_manager_definition)
    uvicorn.run(
        app,
        host=event_manager_definition.manager_config.host,
        port=event_manager_definition.manager_config.port,
    )
