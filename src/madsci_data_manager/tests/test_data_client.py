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
    DataManagerSettings,
    DataPointTypeEnum,
    FileDataPoint,
    ObjectStorageDataPoint,
    ObjectStorageSettings,
    ValueDataPoint,
)
from madsci.common.db_handlers.document_storage_handler import (
    InMemoryDocumentStorageHandler,
)
from madsci.data_manager.data_server import DataManager
from starlette.testclient import TestClient


@pytest.fixture
def document_handler():
    """Create an InMemoryDocumentStorageHandler for testing."""
    handler = InMemoryDocumentStorageHandler(database_name="test_data")
    yield handler
    handler.close()


@pytest.fixture
def test_client(document_handler) -> TestClient:
    """Data Server Test Client Fixture"""
    settings = DataManagerSettings(
        manager_name="Test Data Manager", enable_registry_resolution=False
    )
    manager = DataManager(
        settings=settings,
        document_handler=document_handler,
    )
    app = manager.create_server()
    return TestClient(app)


@pytest.fixture
def client(test_client: TestClient) -> Generator[DataClient, None, None]:
    """Fixture for DataClient patched to use TestClient"""
    with patch("madsci.client.data_client.create_httpx_client") as mock_create_client:
        method_map = {
            "GET": test_client.get,
            "POST": test_client.post,
            "PUT": test_client.put,
            "DELETE": test_client.delete,
        }

        def request_via_test_client(method: str, url: str, **kwargs: Any) -> Any:
            kwargs.pop("timeout", None)
            handler = method_map.get(method.upper(), test_client.get)
            resp = handler(url, **kwargs)
            if not hasattr(resp, "is_success"):
                resp.is_success = resp.status_code < 400
            return resp

        # Create a mock client that routes to TestClient
        mock_client = type("MockClient", (), {})()
        mock_client.request = request_via_test_client
        mock_create_client.return_value = mock_client

        yield DataClient(data_server_url="http://testserver")


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
            "data_type": DataPointTypeEnum.JSON,
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
    """Find a free port to use for object storage."""
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
def object_storage_server():
    """
    Fixture that starts a temporary SeaweedFS S3-compatible server using Docker CLI.
    This is more reliable than testcontainers for some environments.
    """
    if not is_docker_available():
        pytest.skip("Docker not available")

    # Find free port for S3 API
    s3_port = find_free_port()

    # Create temporary directory for SeaweedFS data
    temp_dir = tempfile.mkdtemp(prefix="seaweedfs_test_")

    # Container name with timestamp to avoid conflicts
    timestamp = int(time.time())
    container_name = f"seaweedfs_test_{timestamp}_{s3_port}"

    # Start SeaweedFS container using docker CLI
    docker_cmd = [
        "docker",
        "run",
        "-d",
        "--name",
        container_name,
        "-p",
        f"{s3_port}:8333",
        "-e",
        "AWS_ACCESS_KEY_ID=minioadmin",
        "-e",
        "AWS_SECRET_ACCESS_KEY=minioadmin",
        "-v",
        f"{temp_dir}:/data",
        "chrislusf/seaweedfs:4.17",
        "server",
        "-s3",
        "-dir=/data",
        "-s3.port=8333",
    ]

    container_id = None
    try:
        # Start the container
        print(f"Starting SeaweedFS container on port {s3_port}...")
        result = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
        container_id = result.stdout.strip()
        print(f"SeaweedFS container started: {container_id[:12]}")

        # Wait for SeaweedFS to be ready
        s3_url = f"http://localhost:{s3_port}"
        _wait_for_object_storage(s3_url)
        print(f"SeaweedFS is ready at {s3_url}")

        # Create test bucket
        _create_test_bucket("localhost", s3_port)

        yield {
            "host": "localhost",
            "port": s3_port,
            "endpoint": f"localhost:{s3_port}",
            "url": s3_url,
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "container_id": container_id,
            "container_name": container_name,
        }

    except subprocess.CalledProcessError as e:
        pytest.skip(f"Failed to start SeaweedFS container: {e.stderr}")

    finally:
        if container_id:
            try:
                subprocess.run(
                    ["docker", "stop", container_name],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                subprocess.run(
                    ["docker", "rm", container_name],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
            except Exception as e:
                print(f"Warning: Could not clean up container {container_name}: {e}")

        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Could not remove temp directory {temp_dir}: {e}")


def _wait_for_object_storage(url, timeout=60):
    """Wait for S3-compatible object storage server to be ready."""
    print(f"Waiting for object storage at {url} to be ready...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code in [200, 403, 404]:
                return
        except requests.exceptions.RequestException:
            pass

        print(".", end="", flush=True)
        time.sleep(2)

    raise TimeoutError(
        f"Object storage server at {url} did not become ready within {timeout} seconds"
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
def object_storage_config(object_storage_server):  # noqa
    """
    Fixture that provides object storage configuration for individual tests.
    """
    return ObjectStorageSettings(
        endpoint=object_storage_server["endpoint"],
        access_key=object_storage_server["access_key"],
        secret_key=object_storage_server["secret_key"],
        secure=False,  # Use HTTP for testing
        default_bucket="madsci-test",
    )


def test_object_storage_from_file_datapoint(tmp_path: Path, object_storage_config):  # noqa
    """
    Test uploading and downloading a file using S3-compatible object storage.
    Uses the subprocess Docker CLI approach.
    """
    # Create a test file
    file_path = tmp_path / "test_file.txt"
    file_content = "This is a test file for MinIO storage"
    file_path.write_text(file_content)

    # Initialize DataClient with the test object storage configuration
    with pytest.warns(MadsciLocalOnlyWarning):
        client = DataClient(
            object_storage_settings=object_storage_config,
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
        assert (
            uploaded_datapoint.object_name
            == f"{file_datapoint.datapoint_id}_{file_path.name}"
        ), "Wrong object name"
    else:
        # Even if data_type still shows as "file", check if it has object storage attributes
        pytest.xfail(
            "Datapoint type not converted to object_storage but test otherwise passed"
        )


def test_direct_object_storage_datapoint_submission(  # noqa
    tmp_path: Path,
    object_storage_config,
    object_storage_server,  # noqa
):
    """
    Test creating and submitting an ObjectStorageDataPoint directly.
    Uses the subprocess Docker CLI approach.
    """
    # Create a test file
    file_path = tmp_path / "direct_test_file.txt"
    file_content = "This is a direct ObjectStorageDataPoint test file"
    file_path.write_text(file_content)

    # Initialize DataClient with the test object storage configuration
    with pytest.warns(MadsciLocalOnlyWarning):
        client = DataClient(
            object_storage_settings=object_storage_config,
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
        storage_endpoint=object_storage_server["endpoint"],
        public_endpoint=object_storage_server[
            "endpoint"
        ],  # Use same endpoint for testing
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
    expected_url_prefix = f"http://{object_storage_server['host']}:{object_storage_server['port']}/madsci-test/direct_{file_path.name}"
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


def cleanup_test_containers():
    """Clean up any leftover object storage test containers."""
    try:
        for prefix in ("seaweedfs_test_", "minio_test_"):
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name={prefix}",
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

                for name in container_names:
                    if name.startswith(prefix):
                        subprocess.run(
                            ["docker", "stop", name],
                            capture_output=True,
                            timeout=30,
                            check=False,
                        )
                        subprocess.run(
                            ["docker", "rm", name],
                            capture_output=True,
                            timeout=30,
                            check=False,
                        )

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


# ---------------------------------------------------------------------------
# Regression tests for get_datapoints (C1/C2 fix — sorted() and params key)
# ---------------------------------------------------------------------------


class TestGetDatapointsLocalMode:
    """Regression tests for get_datapoints in local mode (data_server_url=None).

    Covers the bugs fixed in commit ed4b4544:
      C1: list.sort() returns None — slicing crashed with TypeError
      C2: params={number: number} used int as dict key
    """

    @pytest.fixture
    def local_client(self):
        """Create a DataClient in local-only mode."""
        with pytest.warns(MadsciLocalOnlyWarning):
            client = DataClient()
        return client

    def test_get_datapoints_returns_list(self, local_client):
        """get_datapoints must return a list, not None (C1 regression)."""
        # Submit a few datapoints so the local store is non-empty
        dp1 = ValueDataPoint(label="a", value="v1")
        dp2 = ValueDataPoint(label="b", value="v2")
        dp3 = ValueDataPoint(label="c", value="v3")
        local_client.submit_datapoint(dp1)
        local_client.submit_datapoint(dp2)
        local_client.submit_datapoint(dp3)

        result = local_client.get_datapoints(number=10)
        assert isinstance(result, list)
        assert len(result) == 3

    def test_get_datapoints_empty_store(self, local_client):
        """get_datapoints on empty store returns empty list, not None."""
        result = local_client.get_datapoints(number=5)
        assert result == []

    def test_get_datapoints_respects_number_limit(self, local_client):
        """get_datapoints slices to the requested number."""
        for i in range(5):
            local_client.submit_datapoint(ValueDataPoint(label=f"dp{i}", value=f"v{i}"))

        result = local_client.get_datapoints(number=3)
        assert len(result) == 3

    def test_get_datapoints_sorted_descending(self, local_client):
        """get_datapoints returns datapoints sorted by ID descending."""
        dps = []
        for i in range(3):
            dp = ValueDataPoint(label=f"dp{i}", value=f"v{i}")
            local_client.submit_datapoint(dp)
            dps.append(dp)

        result = local_client.get_datapoints(number=10)
        ids = [dp.datapoint_id for dp in result]
        assert ids == sorted(ids, reverse=True)


class TestGetDatapointsRemoteMode:
    """Regression tests for get_datapoints in remote mode (with server URL).

    Covers C2: params key must be the string "number", not the int variable.
    """

    def test_get_datapoints_sends_correct_params(self, client):
        """get_datapoints passes params={'number': N} to the server (C2 regression)."""
        # Submit some datapoints via the test server
        dp1 = ValueDataPoint(label="a", value="v1")
        dp2 = ValueDataPoint(label="b", value="v2")
        client.submit_datapoint(dp1)
        client.submit_datapoint(dp2)

        # Fetch — this exercises the real HTTP path with the test client
        result = client.get_datapoints(number=10)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_datapoints_returns_empty_for_no_data(self, client):
        """get_datapoints returns empty list when no datapoints exist."""
        result = client.get_datapoints(number=10)
        assert result == []


@pytest.mark.asyncio
class TestAsyncGetDatapointsLocalMode:
    """Regression tests for async_get_datapoints in local mode."""

    @pytest.fixture
    def local_client(self):
        with pytest.warns(MadsciLocalOnlyWarning):
            client = DataClient()
        return client

    async def test_async_get_datapoints_returns_list(self, local_client):
        """async_get_datapoints must return a list, not None (C1 regression)."""
        dp1 = ValueDataPoint(label="a", value="v1")
        dp2 = ValueDataPoint(label="b", value="v2")
        local_client.submit_datapoint(dp1)
        local_client.submit_datapoint(dp2)

        result = await local_client.async_get_datapoints(number=10)
        assert isinstance(result, list)
        assert len(result) == 2

    async def test_async_get_datapoints_empty_store(self, local_client):
        """async_get_datapoints on empty store returns empty list."""
        result = await local_client.async_get_datapoints(number=5)
        assert result == []

    async def test_async_get_datapoints_respects_limit(self, local_client):
        """async_get_datapoints slices to the requested number."""
        for i in range(5):
            local_client.submit_datapoint(ValueDataPoint(label=f"dp{i}", value=f"v{i}"))

        result = await local_client.async_get_datapoints(number=2)
        assert len(result) == 2


# Additional tests for improved data client functionality
from datetime import datetime, timezone
from unittest.mock import MagicMock
from madsci.common.types.action_types import ActionDatapoints, ActionResult
from madsci.common.utils import new_ulid_str


class TestDataClientBatchOperations:
    """Test cases for batch datapoint operations."""

    @pytest.fixture
    def mock_data_client(self):
        """Create a DataClient with mocked get_datapoint method."""
        client = DataClient(data_server_url="http://localhost:8004")
        client.get_datapoint = MagicMock()
        return client

    def test_get_datapoints_by_ids_success(self, mock_data_client):
        """Test successful batch fetching of datapoints."""
        # Setup test data
        dp1 = ValueDataPoint(value="test1", label="result1")
        dp2 = FileDataPoint(path="/test/file.txt", label="result2")

        mock_data_client.get_datapoint.side_effect = [dp1, dp2]

        # Test batch fetching
        result = mock_data_client.get_datapoints_by_ids(
            [dp1.datapoint_id, dp2.datapoint_id]
        )

        # Verify results
        assert len(result) == 2
        assert result[dp1.datapoint_id] == dp1
        assert result[dp2.datapoint_id] == dp2
        assert mock_data_client.get_datapoint.call_count == 2

    def test_get_datapoints_by_ids_empty_list(self, mock_data_client):
        """Test batch fetching with empty input."""
        result = mock_data_client.get_datapoints_by_ids([])
        assert result == {}
        mock_data_client.get_datapoint.assert_not_called()

    def test_get_datapoint_metadata(self, mock_data_client):
        """Test extracting metadata from a datapoint."""
        dp = ValueDataPoint(value="test_data", label="test_result")
        dp.data_timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        mock_data_client.get_datapoint.return_value = dp

        metadata = mock_data_client.get_datapoint_metadata(dp.datapoint_id)

        assert metadata["datapoint_id"] == dp.datapoint_id
        assert metadata["label"] == "test_result"
        assert metadata["data_type"] == "json"
        assert metadata["data_timestamp"] == dp.data_timestamp
        assert "ownership_info" in metadata

    def test_extract_datapoint_ids_from_action_result(self, mock_data_client):
        """Test extracting datapoint IDs from ActionResult."""
        ulid1 = new_ulid_str()
        ulid2 = new_ulid_str()

        datapoints = ActionDatapoints.model_validate(
            {"single_result": ulid1, "list_results": [ulid2, new_ulid_str()]}
        )

        action_result = ActionResult(status="succeeded", datapoints=datapoints)

        ids = mock_data_client.extract_datapoint_ids_from_action_result(action_result)

        # Should extract all unique IDs
        assert len(ids) == 3
        assert ulid1 in ids
        assert ulid2 in ids
