"""
Test the Event Manager's REST server.

Uses pytest-mock-resources to create a MongoDB fixture. Note that this _requires_
a working docker installation.
"""

from fastapi.testclient import TestClient
from madsci.common.types.event_types import Event, EventManagerDefinition, EventType
from madsci.event_manager.event_server import EventServer
from pymongo.synchronous.database import Database
from pytest_mock_resources import create_mongo_fixture

db_connection = create_mongo_fixture()

event_manager_def = EventManagerDefinition(
    name="test_event_manager",
)


def test_root(db_connection: Database) -> None:
    """
    Test the root endpoint for the Event_Manager's server.
    Should return an EventManagerDefinition.
    """
    event_manager_server = EventServer(
        event_manager_definition=event_manager_def, db_connection=db_connection
    )
    event_manager_server._configure_routes()
    test_client = TestClient(event_manager_server.app)
    result = test_client.get("/").json()
    EventManagerDefinition.model_validate(result)


def test_roundtrip_event(db_connection: Database) -> None:
    """
    Test that we can send and then retrieve an event by ID.
    """
    event_manager_server = EventServer(
        event_manager_definition=event_manager_def, db_connection=db_connection
    )
    event_manager_server._configure_routes()
    test_client = TestClient(event_manager_server.app)
    test_event = Event(
        event_type=EventType.TEST,
        event_data={"test": "data"},
    )
    result = test_client.post("/event", json=test_event.model_dump(mode="json")).json()
    assert Event.model_validate(result) == test_event
    result = test_client.get(f"/event/{test_event.event_id}").json()
    assert Event.model_validate(result) == test_event


def test_get_events(db_connection: Database) -> None:
    """
    Test that we can retrieve all events and they are returned as a dictionary in reverse-chronological order, with the correct number of events.
    """
    event_manager_server = EventServer(
        event_manager_definition=event_manager_def, db_connection=db_connection
    )
    event_manager_server._configure_routes()
    test_client = TestClient(event_manager_server.app)
    for i in range(10):
        test_event = Event(
            event_type=EventType.TEST,
            event_data={"test": i},
        )
        test_client.post("/event", json=test_event.model_dump(mode="json"))
    query_number = 5
    result = test_client.get("/events", params={"number": query_number}).json()
    # * Check that the number of events returned is correct
    assert len(result) == query_number
    previous_timestamp = float("inf")
    for _, value in result.items():
        event = Event.model_validate(value)
        # * Check that the events are in reverse-chronological order
        assert event.event_data["test"] in range(5, 10)
        assert previous_timestamp >= event.event_timestamp.timestamp()
        previous_timestamp = event.event_timestamp.timestamp()


def test_query_events(db_connection: Database) -> None:
    """
    Test querying events based on a selector.
    """
    event_manager_server = EventServer(
        event_manager_definition=event_manager_def, db_connection=db_connection
    )
    event_manager_server._configure_routes()
    test_client = TestClient(event_manager_server.app)
    for i in range(10, 20):
        test_event = Event(
            event_type=EventType.TEST,
            event_data={"test": i},
        )
        test_client.post("/event", json=test_event.model_dump(mode="json"))
    test_val = 10
    selector = {"event_data.test": {"$gte": test_val}}
    result = test_client.post("/events/query", json=selector).json()
    assert len(result) == test_val
    for _, value in result.items():
        event = Event.model_validate(value)
        assert event.event_data["test"] >= test_val
