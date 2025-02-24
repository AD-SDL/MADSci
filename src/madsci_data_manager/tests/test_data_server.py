"""
Test the Event Manager's REST server.

Uses pytest-mock-resources to create a MongoDB fixture. Note that this _requires_
a working docker installation.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.datapoint_types import (
    DataManagerDefinition,
    LocalFileDataPoint,
    ValueDataPoint,
)
from pymongo.synchronous.database import Database
from pytest_mock_resources import MongoConfig, create_mongo_fixture

from madsci_data_manager.madsci.data_manager.data_server import DataServer

db_connection = create_mongo_fixture()

data_manager_def = DataManagerDefinition(
    name="test_data_manager",
)


@pytest.fixture(scope="session")
def pmr_mongo_config() -> MongoConfig:
    """Congifure the MongoDB fixture."""
    return MongoConfig(image="mongo:8")


def test_root(db_connection: Database) -> None:
    """
    Test the root endpoint for the Event_Manager's server.
    Should return an EventManagerDefinition.
    """
    data_manager_server = DataServer(
        data_manager_definition=data_manager_def, db_connection=db_connection
    )
    data_manager_server._configure_routes()
    test_client = TestClient(data_manager_server.app)
    result = test_client.get("/").json()
    DataManagerDefinition.model_validate(result)


def test_roundtrip_datapoint(db_connection: Database) -> None:
    """
    Test that we can send and then retrieve an datapoint by ID.
    """
    data_manager_server = DataServer(
        data_manager_definition=data_manager_def, db_connection=db_connection
    )
    data_manager_server._configure_routes()
    test_client = TestClient(data_manager_server.app)
    test_datapoint = ValueDataPoint(
        label="test",
        value=5,
    )
    result = test_client.post(
        "/datapoint", data={"datapoint": test_datapoint.model_dump_json()}
    ).json()
    assert ValueDataPoint.model_validate(result) == test_datapoint
    result = test_client.get(f"/datapoint/{test_datapoint.datapoint_id}").json()
    assert ValueDataPoint.model_validate(result) == test_datapoint


def test_roundtrip_file_datapoint(db_connection: Database) -> None:
    """
    Test that we can send and then retrieve an datapoint by ID.
    """
    data_manager_server = DataServer(
        data_manager_definition=data_manager_def, db_connection=db_connection
    )
    data_manager_server._configure_routes()
    test_client = TestClient(data_manager_server.app)
    test_datapoint = LocalFileDataPoint(
        label="test",
        path="/workspaces/MADSci/src/madsci_data_manager/tests/test_data_server.py",
    )
    result = test_client.post(
        "/datapoint",
        data={"datapoint": test_datapoint.model_dump_json()},
        files={
            (
                "files",
                (
                    str(Path(test_datapoint.path).name),
                    Path.open(Path(test_datapoint.path), "rb"),
                ),
            )
        },
    ).json()
    assert LocalFileDataPoint.model_validate(result).label == test_datapoint.label
    result = test_client.get(f"/datapoint/{test_datapoint.datapoint_id}").json()
    assert LocalFileDataPoint.model_validate(result).label == test_datapoint.label


def test_get_datapoints(db_connection: Database) -> None:
    """
    Test that we can retrieve all datapoints and they are returned as a dictionary in reverse-chronological order, with the correct number of datapoints.
    """
    data_manager_server = DataServer(
        data_manager_definition=data_manager_def, db_connection=db_connection
    )
    data_manager_server._configure_routes()
    test_client = TestClient(data_manager_server.app)
    for i in range(10):
        test_datapoint = ValueDataPoint(
            label="test_" + str(i),
            value=i,
        )
        test_client.post(
            "/datapoint", data={"datapoint": test_datapoint.model_dump_json()}
        )
    query_number = 5
    result = test_client.get("/datapoints", params={"number": query_number}).json()
    # * Check that the number of events returned is correct
    assert len(result) == query_number
    previous_timestamp = float("inf")
    for _, value in result.items():
        datapoint = ValueDataPoint.model_validate(value)
        # * Check that the events are in reverse-chronological order
        assert datapoint.value in range(5, 10)
        assert previous_timestamp >= datapoint.data_timestamp.timestamp()
        previous_timestamp = datapoint.data_timestamp.timestamp()


def test_query_datapoints(db_connection: Database) -> None:
    """
    Test querying events based on a selector.
    """
    data_manager_server = DataServer(
        data_manager_definition=data_manager_def, db_connection=db_connection
    )
    data_manager_server._configure_routes()
    test_client = TestClient(data_manager_server.app)
    for i in range(10, 20):
        test_datapoint = ValueDataPoint(
            label="test_" + str(i),
            value=i,
        )
        test_client.post(
            "/datapoint", data={"datapoint": test_datapoint.model_dump_json()}
        )
    test_val = 10
    selector = {"value": {"$gte": test_val}}
    result = test_client.post("/datapoints/query", json=selector).json()
    assert len(result) == test_val
    for _, value in result.items():
        datapoint = ValueDataPoint.model_validate(value)
        assert datapoint.value >= test_val
