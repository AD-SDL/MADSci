"""
Test the Data Manager's REST server.

Uses pytest-mock-resources to create a MongoDB fixture. Note that this _requires_
a working docker installation.
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from madsci.common.types.datapoint_types import (
    DataManagerDefinition,
    FileDataPoint,
    ObjectStorageDefinition,
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


def test_file_datapoint_with_minio(db_connection: Database, tmp_path: Path) -> None:
    """
    Test that file datapoints are uploaded to MinIO object storage when configured.
    """
    from unittest.mock import MagicMock, patch

    # Create a DataManagerDefinition with MinIO configuration
    data_manager_def_with_minio = DataManagerDefinition(
        name="test_data_manager_with_minio",
        minio_client_config=ObjectStorageDefinition(
            endpoint="localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",  # noqa
            secure=False,
            default_bucket="madsci-test",
        ),
    )

    # Mock the MinIO client and its methods
    mock_minio_client = MagicMock()
    mock_minio_client.bucket_exists.return_value = True
    mock_minio_client.fput_object.return_value = MagicMock(etag="test-etag-123")

    # Mock the Minio class to return our mock client
    with patch("minio.Minio", return_value=mock_minio_client):
        # Create the test client with MinIO configuration
        app = create_data_server(
            data_manager_definition=data_manager_def_with_minio, db_client=db_connection
        )
        test_client = TestClient(app)

        # Create a test file
        test_file = tmp_path / "test_minio.txt"
        test_file.expanduser().parent.mkdir(parents=True, exist_ok=True)
        with test_file.open("w") as f:
            f.write("test content for minio")

        # Create a file datapoint
        test_datapoint = FileDataPoint(
            label="test_minio_file",
            path=test_file,
        )

        # Upload the datapoint (following existing pattern)
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
        # Verify MinIO client methods were called
        mock_minio_client.bucket_exists.assert_called_once_with("madsci-test")
        mock_minio_client.fput_object.assert_called_once()

        # Verify the fput_object call arguments
        call_args = mock_minio_client.fput_object.call_args
        assert call_args[1]["bucket_name"] == "madsci-test"
        assert call_args[1]["object_name"].endswith("test_minio.txt")
        assert call_args[1]["content_type"] == "text/plain"

        # Verify the returned datapoint has object storage fields and correct data_type
        assert result["data_type"] == "object_storage"
        assert "bucket_name" in result
        assert "object_name" in result
        assert "storage_endpoint" in result
        assert "url" in result
        assert "etag" in result

        assert result["bucket_name"] == "madsci-test"
        assert result["storage_endpoint"] == "localhost:9000"
        assert result["etag"] == "test-etag-123"
        assert "localhost:9001" in result["url"]  # Should use port 9001 for public URL
        assert (
            result["custom_metadata"]["original_datapoint_id"]
            == test_datapoint.datapoint_id
        )

        # Verify we can retrieve the datapoint with object storage info
        retrieved_result = test_client.get(
            f"/datapoint/{test_datapoint.datapoint_id}"
        ).json()
        assert retrieved_result["data_type"] == "object_storage"
        assert retrieved_result["bucket_name"] == "madsci-test"
        assert retrieved_result["object_name"] == result["object_name"]


@pytest.mark.skipif(
    not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Set RUN_INTEGRATION_TESTS=1 to run integration tests",
)
def test_real_minio_upload(db_connection: Database, tmp_path: Path) -> None:
    """Test actual MinIO upload - requires running MinIO instance"""
    # No mocks - use real MinIO
    data_manager_def_with_minio = DataManagerDefinition(
        name="test_data_manager_with_minio",
        minio_client_config=ObjectStorageDefinition(
            endpoint="localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",  # noqa
            secure=False,
            default_bucket="test-bucket",
        ),
    )

    app = create_data_server(
        data_manager_definition=data_manager_def_with_minio, db_client=db_connection
    )
    test_client = TestClient(app)

    # Create a test file
    test_file = tmp_path / "real_test.txt"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_content = "This is a real test file for MinIO upload!"
    with test_file.open("w") as f:
        f.write(test_content)

    # Create a file datapoint
    test_datapoint = FileDataPoint(
        label="real_minio_test",
        path=test_file,
    )

    # Upload the datapoint to the server
    result = test_client.post(
        "/datapoint",
        data={"datapoint": test_datapoint.model_dump_json()},
        files={
            (
                "files",
                (
                    str(test_file.name),
                    test_file.open("rb"),
                ),
            )
        },
    ).json()

    # Verify the response indicates object storage
    assert result["data_type"] == "object_storage"
    assert result["bucket_name"] == "test-bucket"
    assert result["object_name"].endswith("real_test.txt")
    assert result["size_bytes"] == len(test_content)
    assert "url" in result

    # Optional: Verify the file actually exists in MinIO
    from minio import Minio

    # Create a real MinIO client to verify upload
    real_minio_client = Minio(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",  # noqa
        secure=False,
    )

    # Check if the object exists
    bucket_name = result["bucket_name"]
    object_name = result["object_name"]

    # Try to get object info (this will raise an exception if it doesn't exist)
    object_info = real_minio_client.stat_object(bucket_name, object_name)
    assert object_info.size == len(test_content)

    # Optionally, download and verify content
    response = real_minio_client.get_object(bucket_name, object_name)
    downloaded_content = response.read().decode("utf-8")
    assert downloaded_content == test_content
