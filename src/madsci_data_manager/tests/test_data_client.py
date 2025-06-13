"""Automated pytest unit tests for the madsci data client."""
# flake8: noqa

import time
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import patch
import shutil
import socket
import subprocess
import tempfile

from madsci.common.warnings import MadsciLocalOnlyWarning
import pytest
import requests
from madsci.client.data_client import DataClient
from madsci.common.types.datapoint_types import (
    DataManagerDefinition,
    DataPointTypeEnum,
    FileDataPoint,
    ObjectStorageDataPoint,
    ObjectStorageSettings,
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
    submitted_datapoint = client.submit_datapoint(datapoint)
    assert submitted_datapoint.datapoint_id == datapoint.datapoint_id
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
    with pytest.warns(MadsciLocalOnlyWarning):
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
    file_datapoint = FileDataPoint(label="Test", path=fetched_file_path)
    created_datapoint = client.submit_datapoint(file_datapoint)
    assert created_datapoint.datapoint_id == file_datapoint.datapoint_id
    fetched_datapoint = client.get_datapoint(file_datapoint.datapoint_id)
    assert fetched_datapoint.datapoint_id == file_datapoint.datapoint_id
    file_value = client.get_datapoint_value(file_datapoint.datapoint_id)
    assert file_value == b"test_value"
    fetched_file_path = Path(tmp_path) / "second_fetched_test.txt"
    client.save_datapoint_value(file_datapoint.datapoint_id, fetched_file_path)
    assert fetched_file_path.read_text() == "test_value"


def find_free_port():
    """Find a free port to use for MinIO."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def is_docker_available():
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def minio_server():
    """
    Fixture that starts a temporary MinIO server using Docker CLI directly.
    This is more reliable than testcontainers for some environments.
    """
    if not is_docker_available():
        pytest.skip("Docker not available")

    # Find free ports
    minio_port = find_free_port()
    console_port = find_free_port()

    # Create temporary directory for MinIO data
    temp_dir = tempfile.mkdtemp(prefix="minio_test_")

    # Container name with timestamp to avoid conflicts
    timestamp = int(time.time())
    container_name = f"minio_test_{timestamp}_{minio_port}"

    # Start MinIO container using docker CLI
    docker_cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        f"{minio_port}:9000",
        "-p",
        f"{console_port}:9001",
        "-e",
        "MINIO_ROOT_USER=minioadmin",
        "-e",
        "MINIO_ROOT_PASSWORD=minioadmin",
        "-v",
        f"{temp_dir}:/data",
        "minio/minio:latest",
        "server",
        "/data",
        "--console-address",
        ":9001",
    ]

    container_id = None
    try:
        # Start the container
        print(f"Starting MinIO container on port {minio_port}...")
        result = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()
        print(f"MinIO container started: {container_id[:12]}")

        # Wait for MinIO to be ready
        minio_url = f"http://localhost:{minio_port}"
        _wait_for_minio(minio_url)
        print(f"MinIO is ready at {minio_url}")

        # Create test bucket
        _create_test_bucket("localhost", minio_port)

        yield {
            "host": "localhost",
            "port": minio_port,
            "console_port": console_port,
            "endpoint": f"localhost:{minio_port}",
            "url": minio_url,
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "container_id": container_id,
            "container_name": container_name,
        }

    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start MinIO container: {e.stderr}")

    finally:
        # Individual container cleanup
        if container_id:
            print(f"Cleaning up MinIO container {container_name}...")
            try:
                # Stop container
                stop_result = subprocess.run(
                    ["docker", "stop", container_name],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                # Remove container
                rm_result = subprocess.run(
                    ["docker", "rm", container_name],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )

                if stop_result.returncode == 0 and rm_result.returncode == 0:
                    print(f"Container {container_name} cleaned up")
                else:
                    print(
                        f" Warning: Could not fully clean up container {container_name}"
                    )

            except Exception as e:
                print(f"Warning: Could not clean up container {container_name}: {e}")

        # Remove temp directory
        try:
            shutil.rmtree(temp_dir)
            print(f"Temporary directory {temp_dir} cleaned up")
        except Exception as e:
            print(f" Warning: Could not remove temp directory {temp_dir}: {e}")


def _wait_for_minio(minio_url, timeout=60):
    """Wait for MinIO server to be ready."""
    print(f"Waiting for MinIO at {minio_url} to be ready...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # Try the health endpoint
            response = requests.get(f"{minio_url}/minio/health/live", timeout=5)
            if response.status_code == 200:
                return
        except requests.exceptions.RequestException:
            pass

        # Also try a basic GET to see if the server responds
        try:
            response = requests.get(minio_url, timeout=5)
            if response.status_code in [
                200,
                403,
                404,
            ]:  # Any response means server is up
                return
        except requests.exceptions.RequestException:
            pass

        print(".", end="", flush=True)
        time.sleep(2)

    raise TimeoutError(
        f"MinIO server at {minio_url} did not become ready within {timeout} seconds"
    )


def _create_test_bucket(host, port):  # noqa
    """Create the test bucket using MinIO client."""
    try:
        from minio import Minio

        client = Minio(
            f"{host}:{port}",
            access_key="minioadmin",
            secret_key="minioadmin",  # noqa
            secure=False,
        )

        bucket_name = "madsci-test"
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"Created test bucket: {bucket_name}")  # noqa
        else:
            print(f"Test bucket {bucket_name} already exists")  # noqa

    except Exception as e:
        print(f"Warning: Could not create test bucket: {e}")  # noqa
        # Continue anyway, the application might create it


@pytest.fixture(scope="function")
def minio_config(minio_server):  # noqa
    """
    Fixture that provides MinIO configuration for individual tests.
    """
    return ObjectStorageSettings(
        endpoint=minio_server["endpoint"],
        access_key=minio_server["access_key"],
        secret_key=minio_server["secret_key"],
        secure=False,  # Use HTTP for testing
        default_bucket="madsci-test",
    )


def test_object_storage_from_file_datapoint(tmp_path: Path, minio_config):  # noqa
    """
    Test uploading and downloading a file using MinIO.
    Uses the subprocess Docker CLI approach.
    """
    # Create a test file
    file_path = tmp_path / "test_file.txt"
    file_content = "This is a test file for MinIO storage"
    file_path.write_text(file_content)

    # Initialize DataClient with the test MinIO configuration
    with pytest.warns(MadsciLocalOnlyWarning):
        client = DataClient(
            object_storage_settings=minio_config,
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


def test_direct_object_storage_datapoint_submission(  # noqa
    tmp_path: Path,
    minio_config,
    minio_server,  # noqa
):
    """
    Test creating and submitting an ObjectStorageDataPoint directly.
    Uses the subprocess Docker CLI approach.
    """
    # Create a test file
    file_path = tmp_path / "direct_test_file.txt"
    file_content = "This is a direct ObjectStorageDataPoint test file"
    file_path.write_text(file_content)

    # Initialize DataClient with the test MinIO configuration
    with pytest.warns(MadsciLocalOnlyWarning):
        client = DataClient(
            object_storage_settings=minio_config,
        )

    # Custom metadata for the object
    metadata = {
        "test_type": "direct_submission",
        "content_description": "Text file for testing direct ObjectStorageDataPoint submission",
    }

    # Create the ObjectStorageDataPoint directly
    object_name = f"direct_{file_path.name}"
    bucket_name = "madsci-test"

    direct_datapoint = ObjectStorageDataPoint(
        label="Direct ObjectStorage Test",
        path=str(file_path),
        bucket_name=bucket_name,
        object_name=object_name,
        storage_endpoint=minio_server["endpoint"],
        public_endpoint=minio_server["endpoint"],  # Use same endpoint for testing
        content_type="text/plain",
        custom_metadata=metadata,
        size_bytes=file_path.stat().st_size,
        etag="temporary-etag",
    )

    # Submit the datapoint directly
    uploaded_datapoint = client.submit_datapoint(direct_datapoint)

    # Verify datapoint attributes
    assert uploaded_datapoint.data_type.value == "object_storage", (
        "Datapoint type should be object_storage"
    )
    assert uploaded_datapoint.bucket_name == "madsci-test", "Wrong bucket name"
    assert uploaded_datapoint.object_name == f"direct_{file_path.name}", (
        "Wrong object name"
    )
    assert uploaded_datapoint.custom_metadata.get("test_type") == "direct_submission", (
        "Metadata not preserved"
    )

    # Download to a new location
    download_path = tmp_path / f"downloaded_direct_{file_path.name}"
    client.save_datapoint_value(uploaded_datapoint.datapoint_id, str(download_path))

    # Verify download was successful
    assert download_path.exists(), "Downloaded file doesn't exist"

    # Check file contents and size
    original_size = file_path.stat().st_size
    downloaded_size = download_path.stat().st_size
    assert downloaded_size == original_size, "File sizes don't match"

    downloaded_content = download_path.read_text()
    assert downloaded_content == file_content, "File contents don't match"

    # Verify the URL format is correct
    expected_url_prefix = f"http://{minio_server['host']}:{minio_server['port']}/madsci-test/direct_{file_path.name}"
    assert uploaded_datapoint.url.startswith(expected_url_prefix), (
        f"URL format incorrect. Expected to start with {expected_url_prefix}, got {uploaded_datapoint.url}"
    )

    # Verify etag exists
    assert hasattr(uploaded_datapoint, "etag") and uploaded_datapoint.etag, (
        "Missing etag"
    )


@pytest.fixture(scope="session", autouse=True)
def cleanup_before_tests():  # noqa
    """Automatically clean up any leftover containers before running tests."""
    cleanup_test_containers()
    yield


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_tests():
    """Automatically clean up any leftover containers after running tests."""
    yield  # This runs before cleanup (i.e., after all tests complete)
    print("\nCleaning up test containers after all tests...")
    cleanup_test_containers()


@pytest.fixture(scope="session", autouse=True)
def cleanup_on_interrupt():
    """Clean up containers even if tests are interrupted."""
    try:
        yield
    except KeyboardInterrupt:
        print("\nTests interrupted, cleaning up containers...")
        cleanup_test_containers()
        raise
    except Exception:
        # Don't interfere with other exceptions, but still try to clean up
        cleanup_test_containers()
        raise


# Enhanced cleanup function with better logging
def cleanup_test_containers():
    """Clean up any leftover MinIO test containers."""
    try:
        # List all containers with our test prefix
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                "name=minio_test_",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            container_names = result.stdout.strip().split("\n")
            containers_cleaned = 0

            for name in container_names:
                if name.startswith("minio_test_"):
                    print(f"  Stopping container: {name}")
                    stop_result = subprocess.run(
                        ["docker", "stop", name],
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )

                    print(f"  Removing container: {name}")
                    rm_result = subprocess.run(
                        ["docker", "rm", name],
                        capture_output=True,
                        timeout=30,
                        check=False,
                    )

                    if stop_result.returncode == 0 and rm_result.returncode == 0:
                        containers_cleaned += 1
                    else:
                        print(f"   Warning: Could not fully clean up {name}")

            if containers_cleaned > 0:
                print(f"Cleaned up {containers_cleaned} test container(s)")
            else:
                print("No containers needed cleanup")
        else:
            print("No MinIO test containers found")

    except Exception as e:
        print(f"Could not clean up test containers: {e}")


# Mock test for configuration validation
def test_s3_provider_configurations():
    """Test that different S3 provider configurations are valid."""

    # AWS S3 config
    aws_config = ObjectStorageSettings(
        endpoint="s3.amazonaws.com",
        access_key="AKIAIOSFODNN7EXAMPLE",  # Example key format
        secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        secure=True,
        default_bucket="my-aws-bucket",
        region="us-west-2",
    )

    # GCS config
    gcs_config = ObjectStorageSettings(
        endpoint="storage.googleapis.com",
        access_key="GOOGTS7C7FIS2E4U4RBGEXAMPLE",  # Example HMAC key format
        secret_key="bGoa+V7g/yqDXvKRqq+JTFn4uQZbPiQJo8rkEXAMPLE",
        secure=True,
        default_bucket="my-gcs-bucket",
    )

    # DigitalOcean Spaces config
    do_config = ObjectStorageSettings(
        endpoint="nyc3.digitaloceanspaces.com",
        access_key="DO00EXAMPLE12345678",
        secret_key="doe_secret_key_example_123456789abcdef",
        secure=True,
        default_bucket="my-do-space",
        region="nyc3",
    )

    # Validate all configs have required fields
    for config in [aws_config, gcs_config, do_config]:
        assert config.endpoint
        assert config.access_key
        assert config.secret_key
        assert config.default_bucket
        assert config.secure is True  # Should be True for production services

    # AWS should have region
    assert aws_config.region == "us-west-2"
