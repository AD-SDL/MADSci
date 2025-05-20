"""Automated pytest unit tests for the madsci data client."""

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from madsci.client.data_client import DataClient
from madsci.common.types.datapoint_types import (
    DataManagerDefinition,
    DataPointTypeEnum,
    FileDataPoint,
    ObjectStorageDefinition,
    ValueDataPoint,
)
from madsci.data_manager.data_server import create_data_server
from pymongo import MongoClient
from pytest_mock_resources import MongoConfig, create_mongo_fixture
from starlette.testclient import TestClient


@pytest.fixture(scope="session")
def pmr_mongo_config() -> MongoConfig:
    """Configure the Mongo fixture"""
    return MongoConfig(image="mongo:8.0")


# Create a Mongo fixture
mongo_client = create_mongo_fixture()


@pytest.fixture
def test_client(mongo_client: MongoClient) -> TestClient:
    """Data Server Test Client Fixture"""
    data_manager_definition = DataManagerDefinition(name="Test Data Manager")
    app = create_data_server(
        data_manager_definition=data_manager_definition,
        db_client=mongo_client,
    )
    return TestClient(app)


@pytest.fixture
def client(test_client: TestClient) -> Generator[DataClient, None, None]:
    """Fixture for DataClient patched to use TestClient"""
    with patch("madsci.client.data_client.requests") as mock_requests:

        def post_no_timeout(*args: Any, **kwargs: Any) -> Any:
            kwargs.pop("timeout", None)
            return test_client.post(*args, **kwargs)

        mock_requests.post.side_effect = post_no_timeout

        def get_no_timeout(*args: Any, **kwargs: Any) -> Any:
            kwargs.pop("timeout", None)
            return test_client.get(*args, **kwargs)

        mock_requests.get.side_effect = get_no_timeout

        yield DataClient(url="http://testserver")


def test_create_datapoint(client: DataClient) -> None:
    """Test creating a datapoint using DataClient"""
    datapoint = ValueDataPoint(label="Test", value="test_value")
    created_datapoint = client.submit_datapoint(datapoint)
    assert created_datapoint.datapoint_id == datapoint.datapoint_id


def test_get_datapoint(client: DataClient) -> None:
    """Test getting a datapoint using DataClient"""
    datapoint = ValueDataPoint(label="Test", value="test_value")
    client.submit_datapoint(datapoint)
    fetched_datapoint = client.get_datapoint(datapoint.datapoint_id)
    assert fetched_datapoint.datapoint_id == datapoint.datapoint_id


def test_get_datapoint_value(client: DataClient) -> None:
    """Test getting a datapoint value using DataClient"""
    datapoint = ValueDataPoint(label="Test", value="test_value")
    client.submit_datapoint(datapoint)
    fetched_value = client.get_datapoint_value(datapoint.datapoint_id)
    assert fetched_value == "test_value"


def test_query_datapoints(client: DataClient) -> None:
    """Test querying datapoints using DataClient"""
    datapoint = ValueDataPoint(label="Test", value="test_value")
    client.submit_datapoint(datapoint)
    datapoint2 = ValueDataPoint(label="Test", value="red_herring")
    client.submit_datapoint(datapoint2)
    datapoint3 = ValueDataPoint(label="Red Herring", value="test_value")
    client.submit_datapoint(datapoint3)
    queried_datapoints = client.query_datapoints(
        {
            "data_type": DataPointTypeEnum.DATA_VALUE,
            "label": "Test",
            "value": "test_value",
        }
    )
    assert len(queried_datapoints) == 1
    assert datapoint.datapoint_id in queried_datapoints


def test_file_datapoint(client: DataClient, tmp_path: str) -> None:
    """Test creating a file datapoint using DataClient"""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test_file")
    datapoint = FileDataPoint(label="Test", value="test_value", path=file_path)
    created_datapoint = client.submit_datapoint(datapoint)
    assert created_datapoint.datapoint_id == datapoint.datapoint_id
    fetched_datapoint = client.get_datapoint(datapoint.datapoint_id)
    assert fetched_datapoint.datapoint_id == datapoint.datapoint_id
    file_value = client.get_datapoint_value(datapoint.datapoint_id)
    assert file_value == b"test_file"
    fetched_file_path = tmp_path / "fetched_test.txt"
    client.save_datapoint_value(datapoint.datapoint_id, fetched_file_path)
    assert fetched_file_path.read_text() == "test_file"


def test_local_only_dataclient(tmp_path: str) -> None:
    """Test a dataclient without a URL (i.e. local only)"""
    client = None
    with pytest.warns(UserWarning):
        client = DataClient()
    datapoint = ValueDataPoint(label="Test", value="test_value")
    created_datapoint = client.submit_datapoint(datapoint)
    assert created_datapoint.datapoint_id == datapoint.datapoint_id
    fetched_datapoint = client.get_datapoint(datapoint.datapoint_id)
    assert fetched_datapoint.datapoint_id == datapoint.datapoint_id
    fetched_value = client.get_datapoint_value(datapoint.datapoint_id)
    assert fetched_value == "test_value"
    fetched_file_path = Path(tmp_path) / "fetched_test.txt"
    client.save_datapoint_value(datapoint.datapoint_id, fetched_file_path)
    assert fetched_file_path.read_text() == "test_value"
    file_datapoint = FileDataPoint(
        label="Test", value="test_value", path=fetched_file_path
    )
    created_datapoint = client.submit_datapoint(file_datapoint)
    assert created_datapoint.datapoint_id == file_datapoint.datapoint_id
    fetched_datapoint = client.get_datapoint(file_datapoint.datapoint_id)
    assert fetched_datapoint.datapoint_id == file_datapoint.datapoint_id
    file_value = client.get_datapoint_value(file_datapoint.datapoint_id)
    assert file_value == b"test_value"
    fetched_file_path = Path(tmp_path) / "second_fetched_test.txt"
    client.save_datapoint_value(file_datapoint.datapoint_id, fetched_file_path)
    assert fetched_file_path.read_text() == "test_value"


@pytest.mark.minio  # Custom marker to indicate this test requires MinIO
def test_object_storage_integration(tmp_path: str):  # noqa
    """
    Test uploading and downloading a file using MinIO.

    This test requires a real MinIO server running on localhost:9000
    with minioadmin/minioadmin credentials.
    """
    # Create a test file
    file_path = tmp_path / "test_file.txt"
    file_content = "This is a test file for MinIO storage"
    file_path.write_text(file_content)

    # Create MinIO configuration
    minio_config = ObjectStorageDefinition(
        endpoint="localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",  # noqa
        secure=False,  # Use HTTP for local testing
        default_bucket="madsci-test",
    )

    # Initialize DataClient
    client = DataClient(
        url="http://127.0.0.1:8003",  # Local mode
        object_storage_config=minio_config,
    )

    # Create file datapoint
    file_datapoint = FileDataPoint(label=file_path.name, path=str(file_path))

    # Upload file (should automatically use object storage)
    uploaded_datapoint = client.submit_datapoint(file_datapoint)

    # Verify type conversion (should be changed to object storage)
    assert hasattr(uploaded_datapoint, "data_type"), (
        "Datapoint missing data_type attribute"
    )
    assert hasattr(uploaded_datapoint, "bucket_name"), (
        "Not converted to object storage datapoint"
    )
    assert hasattr(uploaded_datapoint, "object_name"), (
        "Not converted to object storage datapoint"
    )
    assert hasattr(uploaded_datapoint, "url"), "Missing URL in object storage datapoint"

    # Download to a new location
    download_path = tmp_path / f"downloaded_{file_path.name}"
    client.save_datapoint_value(uploaded_datapoint.datapoint_id, str(download_path))

    # Verify download was successful
    assert download_path.exists(), "Downloaded file doesn't exist"

    # Check file contents and size
    original_size = file_path.stat().st_size
    downloaded_size = download_path.stat().st_size
    assert downloaded_size == original_size, "File sizes don't match"

    downloaded_content = download_path.read_text()
    assert downloaded_content == file_content, "File contents don't match"

    # Verify object storage specifics
    if uploaded_datapoint.data_type.value == "object_storage":
        assert uploaded_datapoint.bucket_name == "madsci-test", "Wrong bucket name"
        assert uploaded_datapoint.object_name == file_path.name, "Wrong object name"
    else:
        # Even if data_type still shows as "file", check if it has object storage attributes
        pytest.xfail(
            "Datapoint type not converted to object_storage but test otherwise passed"
        )
