"""
Test the Data Manager's REST server.

Uses pytest-mock-resources to create a MongoDB fixture. Note that this _requires_
a working docker installation.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.datapoint_types import (
    DataManagerDefinition,
    FileDataPoint,
    ValueDataPoint,
)
from madsci.data_manager.data_server import create_data_server
from pymongo.synchronous.database import Database
from pytest_mock_resources import MongoConfig, create_mongo_fixture

data_manager_def = DataManagerDefinition(
    name="test_data_manager",
)


@pytest.fixture(scope="session")
def pmr_mongo_config() -> MongoConfig:
    """Configure the MongoDB fixture."""
    return MongoConfig(image="mongo:8.0")


db_connection = create_mongo_fixture()


@pytest.fixture
def test_client(db_connection: Database) -> TestClient:
    """Data Server Test Client Fixture"""
    app = create_data_server(
        data_manager_definition=data_manager_def, db_client=db_connection
    )
    return TestClient(app)


def test_root(test_client: TestClient) -> None:
    """
    Test the root endpoint for the Data Manager's server.
    Should return a DataManagerDefinition.
    """
    result = test_client.get("/").json()
    DataManagerDefinition.model_validate(result)


def test_roundtrip_datapoint(test_client: TestClient) -> None:
    """
    Test that we can send and then retrieve a datapoint by ID.
    """
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
    value = test_client.get(f"/datapoint/{test_datapoint.datapoint_id}/value")
    assert value.json() == test_datapoint.value


def test_roundtrip_file_datapoint(test_client: TestClient, tmp_path: Path) -> None:
    """
    Test that we can send and then retrieve a datapoint by ID.
    """
    test_file = Path(tmp_path) / "test.txt"
    test_file.expanduser().parent.mkdir(parents=True, exist_ok=True)
    with test_file.open("w") as f:
        f.write("test")
    test_datapoint = FileDataPoint(
        label="test",
        path=test_file,
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
    assert FileDataPoint.model_validate(result).label == test_datapoint.label
    result = test_client.get(f"/datapoint/{test_datapoint.datapoint_id}").json()
    assert FileDataPoint.model_validate(result).label == test_datapoint.label
    value = test_client.get(f"/datapoint/{test_datapoint.datapoint_id}/value")
    assert value.content == b"test"


def test_get_datapoints(test_client: TestClient) -> None:
    """
    Test that we can retrieve all datapoints and they are returned as a dictionary in reverse-chronological order, with the correct number of datapoints.
    """
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


def test_query_datapoints(test_client: TestClient) -> None:
    """
    Test querying events based on a selector.
    """
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
